// ==UserScript==
// @name     websdr-websocket.user.js
// @version  1
// @grant    none
// @match    http://sdr.websdrmaasbree.nl/*
// ==/UserScript==

sock = new WebSocket("ws://localhost:8765/");
sock.addEventListener("message", ({ data }) => {
  unsafeWindow.setfreq(Number(data));
});
