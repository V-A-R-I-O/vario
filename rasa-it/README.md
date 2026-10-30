# VARIO IT Rasa role pack

This is a Rasa Open Source 3.6.20 project. Use Python 3.10 for native
development because Rasa 3.6 does not support Python 3.11 or newer.

## Native run

From the repository root, create and activate a Python 3.10 environment, then
install rasa-it/requirements.txt. In PowerShell:

    py -3.10 -m venv .venv-rasa-it
    .\.venv-rasa-it\Scripts\Activate.ps1
    python -m pip install -r rasa-it/requirements.txt
    $env:PYTHONPATH = (Resolve-Path .\rasa-shared).Path
    Set-Location .\rasa-it
    rasa data validate
    rasa train --fixed-model-name it-model
    rasa run actions --actions actions --port 5055

In a second terminal, activate the same environment and set PYTHONPATH to the
repository's rasa-shared directory, then run:

    Set-Location .\rasa-it
    rasa run --enable-api --port 5006 --credentials credentials.yml --endpoints endpoints.yml

The Rasa server listens on port 5006 and the action server on port 5055. Both
use MOCK_ITSM_URL. The Rasa server uses the shared ADR-006 channel and redacting
SQL tracker store. The security answer is verified from the live turn and is
never retained in a slot or returned to the gateway.

The legacy server.py module remains only for Slice 10 retraining compatibility
tests. It is not the chat runtime; use the Rasa CLI commands above.
