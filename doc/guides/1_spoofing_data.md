# Spoofing data
Spoof available data types to the broker, allowing for demonstration of these elements and rough performance tests.

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

1. Spoofer component startup (**``./src/examples/spoofer``**)

   * Execute **``py -m pip install -r requirements.txt``** to install the module dependencies.

   * Update **``./config.yml``** with the details of the broker to which the Spoofer should connect.

   * Now execute **``py ./main.py``** to effect the Spoofer component.

2. Access the [web app](https://localhost:8081) and set up the processing chain:

   * Create a new chain processing chain, providing all of the relevant details within the available fields.

   * Add the Spoofer component to the chain and configure as appropriate.

3. Verify functionality

---
