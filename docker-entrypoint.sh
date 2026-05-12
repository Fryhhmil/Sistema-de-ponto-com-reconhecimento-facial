#!/bin/sh
set -e

flask db upgrade
exec python -c "from waitress import serve; from app import create_app; serve(create_app(), host='0.0.0.0', port=8000)"
