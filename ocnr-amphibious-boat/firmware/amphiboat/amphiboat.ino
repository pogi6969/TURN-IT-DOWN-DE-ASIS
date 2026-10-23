// Amphibious paddle-wheel boat: ESP32 + TB6612FNG, phone control over Wi-Fi.
// Connect the phone to Wi-Fi "AMPHIBOAT" (password "boat1234"), open http://192.168.4.1
// Left motors (front+rear, wired in parallel) on channel A, right motors on channel B.

#include <WiFi.h>
#include <WebServer.h>

const char *SSID = "AMPHIBOAT";
const char *PASS = "boat1234";

// TB6612FNG pins
const int AIN1 = 26, AIN2 = 25, PWMA = 27;   // left side
const int BIN1 = 14, BIN2 = 12, PWMB = 13;   // right side
const int STBY = 33;

const unsigned long FAILSAFE_MS = 600;       // stop if the phone goes quiet
unsigned long lastCmd = 0;

WebServer server(80);

const char PAGE[] PROGMEM = R"HTML(<!doctype html><html><head>
<meta name=viewport content="width=device-width,initial-scale=1,user-scalable=no">
<style>body{margin:0;font-family:sans-serif;background:#123;color:#fff;text-align:center;touch-action:none}
#pad{width:80vw;height:80vw;max-width:360px;max-height:360px;margin:6vh auto;border-radius:50%;
background:#234;position:relative}#k{width:28%;height:28%;border-radius:50%;background:#f2a33a;
position:absolute;left:36%;top:36%}</style></head><body><h3>AMPHIBOAT</h3><div id=pad><div id=k></div></div>
<p>Drag to drive. Release to stop.</p><script>
const p=document.getElementById('pad'),k=document.getElementById('k');let x=0,y=0,on=false;
function mv(e){const r=p.getBoundingClientRect(),t=e.touches?e.touches[0]:e;
x=Math.max(-1,Math.min(1,(t.clientX-r.left-r.width/2)/(r.width/2)));
y=Math.max(-1,Math.min(1,-(t.clientY-r.top-r.height/2)/(r.height/2)));
k.style.left=(36+x*36)+'%';k.style.top=(36-y*36)+'%';}
function end(){on=false;x=0;y=0;k.style.left='36%';k.style.top='36%';}
p.addEventListener('touchstart',e=>{on=true;mv(e)});p.addEventListener('touchmove',mv);
p.addEventListener('touchend',end);p.addEventListener('mousedown',e=>{on=true;mv(e)});
document.addEventListener('mousemove',e=>{if(on)mv(e)});document.addEventListener('mouseup',end);
setInterval(()=>{const l=Math.round(255*Math.max(-1,Math.min(1,y+x))),
r=Math.round(255*Math.max(-1,Math.min(1,y-x)));fetch('/d?l='+l+'&r='+r).catch(()=>{});},150);
</script></body></html>)HTML";

void setMotor(int in1, int in2, int pwmPin, int speed) {
  speed = constrain(speed, -255, 255);
  digitalWrite(in1, speed > 0);
  digitalWrite(in2, speed < 0);
  analogWrite(pwmPin, abs(speed));
}

void drive(int left, int right) {
  setMotor(AIN1, AIN2, PWMA, left);
  setMotor(BIN1, BIN2, PWMB, right);
}

void handleDrive() {
  drive(server.arg("l").toInt(), server.arg("r").toInt());
  lastCmd = millis();
  server.send(200, "text/plain", "ok");
}

void setup() {
  int pins[] = {AIN1, AIN2, PWMA, BIN1, BIN2, PWMB, STBY};
  for (int p : pins) pinMode(p, OUTPUT);
  digitalWrite(STBY, HIGH);
  drive(0, 0);

  WiFi.softAP(SSID, PASS);
  server.on("/", []() { server.send_P(200, "text/html", PAGE); });
  server.on("/d", handleDrive);
  server.begin();
}

void loop() {
  server.handleClient();
  if (millis() - lastCmd > FAILSAFE_MS) drive(0, 0);
}
