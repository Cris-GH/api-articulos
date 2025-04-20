from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import asyncpg
import os
from dotenv import load_dotenv
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

import asyncio
from contextlib import asynccontextmanager



# Cargar variables de entorno
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configuración de conexión con reintentos
    max_retries = 3
    for attempt in range(max_retries):
        try:
            app.state.db = await asyncpg.connect(
                os.getenv("DATABASE_URL"),
                timeout=10,
                ssl='require'
            )
            print(f"✅ Conexión exitosa (Intento {attempt+1})")
            break
        except Exception as e:
            print(f"⚠️ Error en intento {attempt+1}: {str(e)}")
            if attempt == max_retries - 1:
                raise RuntimeError("No se pudo conectar a la DB después de 3 intentos")
            await asyncio.sleep(2)
    
    yield  # Aquí se ejecuta tu aplicación
    
    if hasattr(app.state, 'db'):
        await app.state.db.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://api-web-two-iota.vercel.app/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

DATABASE_URL = os.getenv("DATABASE_URL")
conn = None

class ArticuloBase(BaseModel):
    idcategoria: Optional[int] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    stock: Optional[int] = None
    

async def get_db():
    return await asyncpg.connect(
        os.getenv("DATABASE_URL"),
        ssl={
            'sslmode': 'require',
            'sslrootcert': '/etc/ssl/certs/ca-certificates.crt'
        }
    )

@app.on_event("startup")
async def startup():
    global conn
    conn = await asyncpg.connect(DATABASE_URL)

@app.on_event("shutdown")
async def shutdown():
    await conn.close()

# Endpoints CRUD
@app.post("/articulos") 
async def crear_articulo(articulo:ArticuloBase):
    await conn.execute(
        """INSERT INTO public.articulo 
            (idcategoria, nombre, descripcion, stock) 
            VALUES ($1, $2, $3, $4) 
            RETURNING idarticulo, idcategoria, nombre, descripcion, stock""",
            articulo.idcategoria, articulo.nombre, 
            articulo.descripcion, articulo.stock
    )
    return {"mensaje": "Articulo agregado"}

@app.get("/articulos")
async def listar_articulos():
    rows = await conn.fetch("SELECT * FROM public.articulo ORDER BY idarticulo")
    return [dict(row) for row in rows]

@app.get("/articulos/{idarticulo}")
async def obtener_articulo(idarticulo: int):
    row = await conn.fetchrow(
        "SELECT * FROM public.articulo WHERE idarticulo = $1", 
        idarticulo
    )
    return dict(row)

@app.put("/articulos/{idarticulo}")
async def actualizar_articulo(idarticulo: int, articulo: ArticuloBase):
    result = await conn.execute(
        """UPDATE public.articulo 
            SET idcategoria=$1, nombre=$2, descripcion=$3, stock=$4 
            WHERE idarticulo=$5 
            RETURNING idarticulo, idcategoria, nombre, descripcion, stock""",
            articulo.idcategoria, articulo.nombre, 
            articulo.descripcion, articulo.stock, idarticulo
    )
    return {"mensaje": "Articulo actualizado"}

@app.delete("/articulos/{idarticulo}")
async def eliminar_articulo(idarticulo: int):
    await conn.execute("DELETE FROM public.articulo WHERE idarticulo=$1", 
            idarticulo)
    return {"mensaje": "Articulo eliminado"}

@app.get("/debug-db")
async def debug_db():
    try:
        await app.state.db.execute("SELECT 1")
        return {"db_status": "connected"}
    except Exception as e:
        return {"db_status": "error", "details": str(e)}
