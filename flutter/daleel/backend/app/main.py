import importlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from . import config
from .api import bookings, conversations, guardrails, handoffs, leads, properties, system
from .database import init_db, make_engine, make_session_factory
from .errors import install_handlers
from .integrations.contracts import ModuleRegistry
from .models import Lead


def create_app(database_url: str | None = None, auto_seed: bool | None = None) -> FastAPI:
    app = FastAPI(title="Daleel AI - Real Estate Sales Sandbox", version=config.APP_VERSION,
                  description=config.DEMO_NOTICE)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    install_handlers(app)

    engine = make_engine(database_url or config.DATABASE_URL)
    init_db(engine)
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    app.state.registry = ModuleRegistry()

    if config.AUTO_SEED if auto_seed is None else auto_seed:
        from .seed import seed_database
        with app.state.session_factory() as db:
            if not db.scalar(select(func.count()).select_from(Lead)):
                seed_database(db)

    # Local providers are optional; the checked-in extension hook registers none by default.
    try:
        ext = importlib.import_module("app.extensions")
    except ModuleNotFoundError as e:
        if e.name not in ("app.extensions", "app"):
            raise
    else:
        ext.register(app.state.registry)

    for r in (system.router, leads.router, properties.router, bookings.router, handoffs.router,
              conversations.router, guardrails.router):
        app.include_router(r)
    return app


app = create_app()
