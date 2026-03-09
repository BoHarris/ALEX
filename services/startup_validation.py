import logging

logger = logging.getLogger(__name__)


def run_startup_validations() -> None:
    """
    Central startup validation entrypoint.
    Add non-route, environment/runtime safety checks here as needed.
    """
    logger.info("Startup validation: no blocking startup validations configured.")
