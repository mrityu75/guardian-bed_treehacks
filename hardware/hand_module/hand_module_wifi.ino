/*
 BED MODULE with WiFi HTTP Server
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ===== CHANGE THESE TO YOUR WIFI =====
const char* ssid = "iphone";
const char* password = "";
// ======================================

const int PIN_SDA = 21;
const int PIN_SCL = 22;
const int PIN_DS18B20 = 27;
const int PIN_MIC1 = 14;
const int PIN_MIC2 = 12;
const int PIN_MIC3 = 13;

const int NUM_FSR = 12;
const int FSR_PINS[NUM_FSR] = {36, 39, 34, 35, 32, 33, 25, 26, 4, 0, 2, 15};

const uint8_t ADDR_MPU1 = 0x68;
const uint8_t ADDR_MPU2 = 0x69;

Adafruit_MPU6050 mpu1;
Adafruit_MPU6050 mpu2;
OneWire oneWire(PIN_DS18B20);
DallasTemperature ds18b20(&oneWire);

DeviceAddress tempAddress[3];
int tempSensorCount = 0;

WebServer server(80);

void setupDS18B20() {
  ds18b20.begin();
  tempSensorCount = ds18b20.getDeviceCount();
  Serial.print("DS18B20 sensors found: ");
  Serial.println(tempSensorCount);
  
  for (int i = 0; i < tempSensorCount && i < 3; i++) {
    if (ds18b20.getAddress(tempAddress[i], i)) {
      Serial.print("  Sensor ");
      Serial.print(i);
      Serial.println(" OK");
    }
  }
}

void handleData() {
  StaticJsonDocument<2048> doc;
  
  doc["timestamp"] = millis();
  doc["module"] = "bed";
  
  JsonArray fsrs = doc.createNestedArray("fsrs");
  for (int i = 0; i < NUM_FSR; i++) {
    fsrs.add(analogRead(FSR_PINS[i]));
  }
  
  JsonArray temps = doc.createNestedArray("temperatures");
  if (tempSensorCount > 0) {
    ds18b20.requestTemperatures();
    for (int i = 0; i < tempSensorCount && i < 3; i++) {
      float tempC = ds18b20.getTempC(tempAddress[i]);
      temps.add(tempC);
    }
  }
  
  JsonObject mpu1_obj = doc.createNestedObject("mpu1");
  sensors_event_t a1, g1, t1;
  if (mpu1.getAccelerometerSensor() != nullptr) {
    mpu1.getEvent(&a1, &g1, &t1);
    
    JsonObject mpu1_accel = mpu1_obj.createNestedObject("accel");
    mpu1_accel["x"] = a1.acceleration.x;
    mpu1_accel["y"] = a1.acceleration.y;
    mpu1_accel["z"] = a1.acceleration.z;
    
    JsonObject mpu1_gyro = mpu1_obj.createNestedObject("gyro");
    mpu1_gyro["x"] = g1.gyro.x;
    mpu1_gyro["y"] = g1.gyro.y;
    mpu1_gyro["z"] = g1.gyro.z;
  }
  
  JsonObject mpu2_obj = doc.createNestedObject("mpu2");
  sensors_event_t a2, g2, t2;
  if (mpu2.getAccelerometerSensor() != nullptr) {
    mpu2.getEvent(&a2, &g2, &t2);
    
    JsonObject mpu2_accel = mpu2_obj.createNestedObject("accel");
    mpu2_accel["x"] = a2.acceleration.x;
    mpu2_accel["y"] = a2.acceleration.y;
    mpu2_accel["z"] = a2.acceleration.z;
    
    JsonObject mpu2_gyro = mpu2_obj.createNestedObject("gyro");
    mpu2_gyro["x"] = g2.gyro.x;
    mpu2_gyro["y"] = g2.gyro.y;
    mpu2_gyro["z"] = g2.gyro.z;
  }
  
  JsonArray mics = doc.createNestedArray("microphones");
  mics.add(analogRead(PIN_MIC1));
  mics.add(analogRead(PIN_MIC2));
  mics.add(analogRead(PIN_MIC3));
  
  String output;
  serializeJson(doc, output);
  
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.send(200, "application/json", output);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n========================================");
  Serial.println("BED MODULE - WiFi HTTP Server");
  Serial.println("========================================\n");
  
  Wire.begin(PIN_SDA, PIN_SCL);
  
  Serial.print("Initializing MPU6050 #1... ");
  if (mpu1.begin(ADDR_MPU1)) {
    Serial.println("OK");
    mpu1.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu1.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu1.setFilterBandwidth(MPU6050_BAND_21_HZ);
  } else {
    Serial.println("FAILED");
  }
  
  Serial.print("Initializing MPU6050 #2... ");
  if (mpu2.begin(ADDR_MPU2)) {
    Serial.println("OK");
    mpu2.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu2.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu2.setFilterBandwidth(MPU6050_BAND_21_HZ);
  } else {
    Serial.println("FAILED");
  }
  
  Serial.print("Initializing DS18B20... ");
  setupDS18B20();
  
  Serial.print("\nConnecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n WiFi Connected!");
    Serial.print(" IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.print(" Access at: http://");
    Serial.print(WiFi.localIP());
    Serial.println("/data");
  } else {
    Serial.println("\n WiFi FAILED!");
  }
  
  server.on("/data", handleData);
  server.begin();
  
  Serial.println("\n========================================");
  Serial.println("Server running!");
  Serial.println("========================================\n");
}

void loop() {
  server.handleClient();
  delay(1);
}