// #include <WiFi.h>
// #include <Adafruit_NeoPixel.h>

// // Wi-Fi credentials
// const char* ssid = "Oscar";
// const char* password = "password";

// // Onboard RGB LED
// #define LED_PIN 38     // Confirmed for Waveshare N8R8
// #define NUM_PIXELS 1
// Adafruit_NeoPixel pixels(NUM_PIXELS, LED_PIN, NEO_GRB + NEO_KHZ800);

// void setup() {
//   Serial.begin(115200);
//   pixels.begin();
//   pixels.clear();
//   pixels.show();

//   Serial.println("Connecting to Wi-Fi...");
//   WiFi.begin(ssid, password);

//   int attempts = 0;
//   while (WiFi.status() != WL_CONNECTED && attempts < 20) {
//     pixels.setPixelColor(0, pixels.Color(255, 165, 0)); // orange while connecting
//     pixels.show();
//     delay(250);
//     pixels.clear();
//     pixels.show();
//     delay(250);
//     attempts++;
//   }

//   if (WiFi.status() == WL_CONNECTED) {
//     Serial.println("✅ Wi-Fi connected!");
//     Serial.print("IP address: ");
//     Serial.println(WiFi.localIP());
//     pixels.setPixelColor(0, pixels.Color(0, 255, 0)); // green = success
//     pixels.show();
//   } else {
//     Serial.println("❌ Wi-Fi connection failed.");
//     pixels.setPixelColor(0, pixels.Color(255, 0, 0)); // red = failed
//     pixels.show();
//   }
// }

// void loop() {
//   // Optionally, blink every 2 seconds if connected
//   if (WiFi.status() == WL_CONNECTED) {
//     pixels.setPixelColor(0, pixels.Color(0, 255, 255));
//     pixels.show();
//     delay(200);
//     pixels.clear();
//     pixels.show();
//     delay(1800);
//   }
// }
