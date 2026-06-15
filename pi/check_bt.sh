#!/bin/bash
cd ~/obd2-adapter
python3 -c "import sys; print(sys.version)"
python3 -c "import bluetooth; print('bluetooth module imported OK')" 2>&1 || echo "bluetooth module FAILED"
python3 -c "import bluetooth; print(bluetooth.__version__)" 2>&1 || echo "no __version__"