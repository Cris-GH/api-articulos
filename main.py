from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import asyncpg
import os
from dotenv import load_dotenv
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    title="API de Artículos",
    description="API para gestión de artículos con Supabase",
    version="1.0.0"
)

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
