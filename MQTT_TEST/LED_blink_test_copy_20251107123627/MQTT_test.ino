// #include <WiFi.h>
// #include <PubSubClient.h>
// #include <Adafruit_NeoPixel.h>

// // WiFi credentials
// const char* ssid = "Oscar";
// const char* password = "password";

// // MQTT broker (MacBook’s IP)
// const char* mqtt_server = "172.20.10.3"; // <-- replace with Mac's IP

// WiFiClient espClient;
// PubSubClient client(espClient);

// // Onboard RGB LED
// #define LED_PIN 38
// #define NUM_PIXELS 1
// Adafruit_NeoPixel pixels(NUM_PIXELS, LED_PIN, NEO_GRB + NEO_KHZ800);

// void setup_wifi() {
//   delay(10);
//   Serial.println("Connecting to WiFi...");
//   WiFi.begin(ssid, password);
//   while (WiFi.status() != WL_CONNECTED) {
//     delay(500);
//     Serial.print(".");
//   }
//   Serial.println("");
//   Serial.print("Connected! IP: ");
//   Serial.println(WiFi.localIP());
// }

// void reconnect() {
//   while (!client.connected()) {
//     Serial.print("Connecting to MQTT...");
//     if (client.connect("ESP32Client")) {
//       Serial.println("connected!");
//       pixels.setPixelColor(0, pixels.Color(0, 255, 0)); // Green when connected
//       pixels.show();
//     } else {
//       Serial.print("failed, rc=");
//       Serial.print(client.state());
//       Serial.println(" try again in 5 seconds");
//       pixels.setPixelColor(0, pixels.Color(255, 0, 0)); // Red on fail
//       pixels.show();
//       delay(5000);
//     }
//   }
// }

// void setup() {
//   Serial.begin(115200);
//   pixels.begin();
//   setup_wifi();
//   client.setServer(mqtt_server, 1883);
// }

// void loop() {
//   if (!client.connected()) {
//     reconnect();
//   }
//   client.loop();

//   // Publish test data
//   static int counter = 0;
//   String payload = "Test message #" + String(counter++);
//   client.publish("esp32/test", payload.c_str());
//   Serial.println("Sent: " + payload);

//   delay(2000);
// }
