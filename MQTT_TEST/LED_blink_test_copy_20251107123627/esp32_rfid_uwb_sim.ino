// #include <WiFi.h>
// #include <PubSubClient.h>
// #include <ArduinoJson.h>

// const char* ssid = "Oscar";
// const char* password = "password";
// const char* mqtt_server = "172.20.10.3";

// WiFiClient espClient;
// PubSubClient client(espClient);

// const float y_fixed = 3.8;         // scanner path
// float x_pos = 2.1;
// bool forward = true;
// const float x_min = 2.1, x_max = 2.6;
// float step_size = 0.025;

// const int NUM_ITEMS = 50;
// float item_x[NUM_ITEMS];
// float item_y[NUM_ITEMS];
// int stock_levels[NUM_ITEMS];
// bool initialized = false;
// bool start_signal = false;

// void setup_wifi() {
//   Serial.println("Connecting to WiFi...");
//   WiFi.mode(WIFI_STA);
//   WiFi.begin(ssid, password);
//   while (WiFi.status() != WL_CONNECTED) {
//     delay(500);
//     Serial.print(".");
//   }
//   Serial.println("\nConnected to WiFi!");
//   Serial.print("ESP32 IP: ");
//   Serial.println(WiFi.localIP());
// }

// void reconnect() {
//   while (!client.connected()) {
//     Serial.print("Connecting to MQTT...");
//     if (client.connect("ESP32_AisleSim")) {
//       Serial.println("connected!");
//       client.subscribe("store/control");
//       client.publish("store/status", "ESP32_READY");
//     } else {
//       Serial.print("failed, rc=");
//       Serial.print(client.state());
//       Serial.println(" retrying...");
//       delay(2000);
//     }
//   }
// }

// void callback(char* topic, byte* payload, unsigned int length) {
//   String msg;
//   for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
//   if (msg == "START") {
//     start_signal = true;
//     Serial.println("Received START signal from server!");
//   }
// }

// String generateData() {
//   StaticJsonDocument<2048> doc;
//   doc["timestamp"] = millis();
//   doc["location"]["x"] = x_pos;
//   doc["location"]["y"] = y_fixed;

//   JsonArray detections = doc.createNestedArray("detections");
//   for (int i = 0; i < NUM_ITEMS; i++) {
//     float dx = item_x[i] - x_pos;
//     float dy = item_y[i] - y_fixed;
//     float dist = sqrt(dx * dx + dy * dy);

//     // very tight detection radius (~5 cm)
//     if (dist < 0.05) {
//       JsonObject d = detections.createNestedObject();
//       d["id"] = String("EPC") + String(i + 1);
//       d["name"] = String("Item_") + String(i + 1);
//       d["count"] = stock_levels[i];

//       // occasional depletion after first full pass
//       if (initialized && random(0, 100) < 4 && stock_levels[i] > 0) {
//         stock_levels[i]--;
//       }
//     }
//   }

//   String out;
//   serializeJson(doc, out);
//   return out;
// }

// void setup() {
//   Serial.begin(115200);
//   setup_wifi();
//   client.setServer(mqtt_server, 1883);
//   client.setBufferSize(4096);
//   client.setCallback(callback);
//   reconnect();
//   randomSeed(analogRead(0));

//   // Two shelves positioned close to scanner line, ±5 cm
//   for (int i = 0; i < NUM_ITEMS; i++) {
//     item_x[i] = x_min + (x_max - x_min) * i / (NUM_ITEMS - 1);

//     // Alternate between top (3.85) and bottom (3.75)
//     if (i % 2 == 0)
//       item_y[i] = 3.85 + random(-5, 5) * 0.001; // ±0.5 cm variance
//     else
//       item_y[i] = 3.75 + random(-5, 5) * 0.001;

//     stock_levels[i] = 2;
//   }
// }

// void loop() {
//   if (!client.connected()) reconnect();
//   client.loop();

//   if (!start_signal) {
//     delay(500);
//     return;
//   }

//   String payload = generateData();
//   if (payload.indexOf("\"detections\":[]") == -1) {
//     client.publish("store/aisle1", payload.c_str());
//     Serial.println(payload);
//   }

//   // simulate walking
//   if (forward) x_pos += step_size;
//   else x_pos -= step_size;
//   if (x_pos >= x_max) { forward = false; initialized = true; }
//   if (x_pos <= x_min) forward = true;

//   delay(300);
// }
