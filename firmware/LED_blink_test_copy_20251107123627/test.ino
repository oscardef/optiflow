// #include <WiFi.h>
// #include <PubSubClient.h>

// const char* ssid = "Oscar";
// const char* password = "password";
// const char* mqtt_server = "172.20.10.3"; // your Mac's IP on the hotspot

// WiFiClient espClient;
// PubSubClient client(espClient);

// void setup() {
//   Serial.begin(115200);
//   WiFi.begin(ssid, password);
//   Serial.print("Connecting to WiFi");
//   while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
//   Serial.println("\nConnected to WiFi");
//   Serial.print("IP: "); Serial.println(WiFi.localIP());

//   client.setServer(mqtt_server, 1883);
// }

// void loop() {
//   if (!client.connected()) {
//     Serial.print("Connecting to MQTT at ");
//     Serial.print(mqtt_server);
//     if (client.connect("ESP32TestClient")) {
//       Serial.println(" -> connected!");
//     } else {
//       Serial.print(" -> failed, rc=");
//       Serial.println(client.state());
//       delay(5000);
//       return;
//     }
//   }
//   client.publish("esp32/test", "hello_from_esp32");
//   Serial.println("Published: hello_from_esp32");
//   delay(2000);
// }
