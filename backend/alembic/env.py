from logging.config import fileConfig

from alembic import context

from app.core.config import get_settings
from app.core.db import Base
import app.modules.auth.models  # noqa: F401
import app.modules.claims.models  # noqa: F401
import app.modules.dividend.models  # noqa: F401
import app.modules.invites.models  # noqa: F401
import app.modules.ledger.models  # noqa: F401
import app.modules.memberships.models  # noqa: F401
import app.modules.public_account.models  # noqa: F401
import app.modules.recurring.models  # noqa: F401
import app.modules.stores.models  # noqa: F401
import app.modules.transfers.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    connectable = create_engine(get_settings().database_url)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
