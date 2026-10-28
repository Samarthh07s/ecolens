/* Approximate noise level from the browser microphone (Web Audio API).

   HONEST DISCLAIMER: browsers give us a digital signal level (dBFS, where
   0 is the loudest the mic can capture), not sound pressure (dB SPL).
   We add a fixed offset of ~100 dB, which places a quiet room near 35-40 dB
   and normal speech near 60-70 dB on typical laptop/phone mics. The result
   is an uncalibrated estimate and can be off by 10 dB or more.

   Nothing is recorded: audio samples are analysed in memory and discarded;
   only the final dB number is sent to the server. */
(function () {
  "use strict";

  var CALIBRATION_OFFSET = 100;   // dBFS -> approximate dB SPL
  var MIN_DB = 20, MAX_DB = 120;

  function measure(opts) {
    opts = opts || {};
    var seconds = opts.seconds || 5;
    var onLevel = opts.onLevel || function () {};

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return Promise.reject(new Error("This browser cannot access the microphone. Use Chrome or Edge, " +
        "and open the app at http://127.0.0.1:5000 (not a file:// path)."));
    }
    var AudioCtx = window.AudioContext || window.webkitAudioContext;

    return navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }
    }).catch(function (e) {
      if (e && (e.name === "NotAllowedError" || e.name === "SecurityError")) {
        throw new Error("Microphone permission was denied. Allow it from the lock icon in the address bar, or type a dB value manually.");
      }
      if (e && e.name === "NotFoundError") throw new Error("No microphone was found. Enter a dB value manually instead.");
      throw new Error("Could not start the microphone: " + (e && e.message ? e.message : e));
    }).then(function (stream) {
      var ctx = new AudioCtx();
      var src = ctx.createMediaStreamSource(stream);
      var analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      src.connect(analyser);
      var buf = new Float32Array(analyser.fftSize);
      var energies = [];
      var start = performance.now();

      return new Promise(function (resolve) {
        function frame(now) {
          analyser.getFloatTimeDomainData(buf);
          var sum = 0;
          for (var i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
          var rms = Math.sqrt(sum / buf.length);
          var db = rms > 0 ? 20 * Math.log10(rms) + CALIBRATION_OFFSET : MIN_DB;
          db = Math.max(MIN_DB, Math.min(MAX_DB, db));
          energies.push(Math.pow(10, db / 10));
          onLevel(db, Math.min(1, (now - start) / (seconds * 1000)));

          if (now - start < seconds * 1000) {
            requestAnimationFrame(frame);
          } else {
            stream.getTracks().forEach(function (t) { t.stop(); });
            ctx.close();
            // Equivalent continuous level (Leq): average the energy, not the dB values
            var mean = energies.reduce(function (a, b) { return a + b; }, 0) / Math.max(1, energies.length);
            resolve(Math.round(10 * Math.log10(mean) * 10) / 10);
          }
        }
        requestAnimationFrame(frame);
      });
    });
  }

  function band(db) {
    if (db === null || db === undefined) return { label: "Not measured yet", level: "none" };
    if (db < 40) return { label: "Quiet", level: "good" };
    if (db < 60) return { label: "Normal", level: "moderate" };
    if (db < 80) return { label: "Loud", level: "usg" };
    return { label: "Harmful", level: "unhealthy" };
  }

  window.EcoNoise = { measure: measure, band: band, MIN_DB: MIN_DB, MAX_DB: MAX_DB };
})();
