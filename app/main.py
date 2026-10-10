import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

import app.models  # noqa: E402,F401  (registra los modelos ORM)
from app.api import medicion, sensor, sensor_magnitud  # noqa: E402
from app.mqtt.client import start_mqtt, stop_mqtt  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_mqtt()
    yield
    stop_mqtt()


app = FastAPI(title="Taller 2 - API IoT", lifespan=lifespan)
app.include_router(sensor.router)
app.include_router(sensor_magnitud.router)
app.include_router(medicion.router)
