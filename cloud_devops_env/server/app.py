"""
CloudDevOps-Env: FastAPI Server
Wires up the environment using OpenEnv's create_fastapi_app helper.
"""

import uvicorn
from openenv.core.env_server import create_fastapi_app
from environment import CloudDevOpsEnvironment
from models import CloudAction, CloudObservation

app = create_fastapi_app(CloudDevOpsEnvironment, CloudAction, CloudObservation)


def main():
    """Entry point for the server."""
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
