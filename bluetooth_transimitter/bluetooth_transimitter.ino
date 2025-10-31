#include <SoftwareSerial.h>
SoftwareSerial bt(10, 11); // RX, TX
void setup(){
 Serial.begin(38400); 
 bt.begin(38400); 
}
void loop(){
 if(Serial.available()){
   bt.write(Serial.read());
 }

 if(bt.available()){
  Serial.print(bt.readString()); 
 }
}