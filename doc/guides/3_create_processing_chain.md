# Create processing chain
Full processing chain, with the first component emulating data, the second processing the data and a third forming tracks on the processed data.

> Note: This is primarily concerned with the mechanisms on an operational level, these components are not intended for use with raw radar data - as is - but may be adapted for such.

---
## Setting up the environment
Local network deployment of the directory server, along with a locally running MQTT broker for data transfers.

1. Run the MQTT broker

2. Start web server

3. Verify web app availability [https://localhost:8081]

4. Connect to the broker [WS  - localhost - 9001]

5. [OPTIONAL] Install the web app to desktop

6. [OPTIONAL] Start up MQTT-Spy to monitor data transfers over the broker

---
## Setting up the processing chain
Effect the example to a chain and verify.

1. Emulator component startup (**``./src/examples/emulator``**)

   * Execute **``py -m pip install -r requirements.txt``** to install the module dependencies.

   * Update **``./config.yml``** with the details of the broker to which the Emulator should connect.

   * Now execute **``py ./main.py``** to effect the Emulator component.

2. Processor component startup (**``./src/examples/processor``**)

   * Execute **``py -m pip install -r requirements.txt``** to install the module dependencies.

   * Update **``./config.yml``** with the details of the broker to which the Processor should connect.

   * Now execute **``py ./main.py``** to effect the Processor component.

2. Matlab based Tracker component startup (**``./src/examples/tracker_matlab``**)

   * Execute **``py -m pip install -r requirements.txt``** to install the module dependencies.

   * Update **``./config.yml``** with the details of the broker to which the Matlab based Tracker should connect.

   * Now execute **``py ./main.py``** to effect the Matlab based Tracker component.

4. Access the [web app](https://localhost:8081) and set up the processing chain:

   * Create a new chain processing chain, providing all of the relevant details within the available fields.

   * Add the Emulator component to the chain and configure as appropriate.

   * Add the Processor component to the chain and configure as appropriate.

   * Add the Tracker component to the chain and configure as appropriate.

5. Verify functionality

---
