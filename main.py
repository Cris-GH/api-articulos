from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import asyncpg
import os
from dotenv import load_dotenv
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await asyncpg.create_pool(
        os.getenv("DATABASE_URL"),
        min_size=1,
        max_size=5,
        ssl='require'
    )
    yield
    await app.state.pool.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    
@app.on_event("startup")
async def startup():
    global conn
    try:
        app.state.pool = await asyncpg.create_pool(
            os.getenv("DATABASE_URL"),
            min_size=1,
            max_size=10
        )
        print("¡Conexión exitosa a la base de datos!")
    except Exception as e:
        print(f"Error de conexión: {str(e)}")
        raise   

@app.on_event("shutdown")
async def shutdown():
    await conn.close()

# Endpoints CRUD
@app.post("/articulos")
async def crear_articulo(articulo: ArticuloBase):
    async with app.state.pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO public.articulo 
                (idcategoria, nombre, descripcion, stock) 
                VALUES ($1, $2, $3, $4) 
                RETURNING idarticulo""",
            articulo.idcategoria, articulo.nombre, 
            articulo.descripcion, articulo.stock
        )
    return {"mensaje": "Artículo agregado"}

@app.get("/articulos")
async def listar_articulos():
    async with app.state.pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM public.articulo")
    return [dict(row) for row in rows]

@app.get("/articulos/{idarticulo}")
async def obtener_articulo(idarticulo: int):
    async with app.state.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM public.articulo WHERE idarticulo = $1", 
            idarticulo
        )
    if not row:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return dict(row)

@app.put("/articulos/{idarticulo}")
async def actualizar_articulo(idarticulo: int, articulo: ArticuloBase):
    async with app.state.pool.acquire() as conn:
        updated = await conn.execute(
            """UPDATE public.articulo 
                SET idcategoria=$1, nombre=$2, descripcion=$3, stock=$4 
                WHERE idarticulo=$5""",
            articulo.idcategoria, articulo.nombre, 
            articulo.descripcion, articulo.stock, idarticulo
        )
        if "UPDATE 0" in updated:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return {"mensaje": "Artículo actualizado"}

@app.delete("/articulos/{idarticulo}")
async def eliminar_articulo(idarticulo: int):
    async with app.state.pool.acquire() as conn:
        deleted = await conn.execute(
            "DELETE FROM public.articulo WHERE idarticulo=$1", 
            idarticulo
        )
        if "DELETE 0" in deleted:
            raise HTTPException(status_code=404, detail="Artículo no encontrado")
    return {"mensaje": "Artículo eliminado"}
