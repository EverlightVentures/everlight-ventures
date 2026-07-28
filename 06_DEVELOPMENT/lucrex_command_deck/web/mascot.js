/* mascot.js -- "The Winner" (BCARDD) as a living 3D portrait, docked in the
   sidebar. Cover-crops to the crown/face so it reads as an avatar in a short
   box; keeps parallax tilt, mood glow, wake-in, and ambient embers.
   Falls back to a cropped CSS image if WebGL/three is unavailable. */
(function () {
  "use strict";
  var MOODS = {
    idle: { glow: 0.35, fire: 0.30, lines: ["The edge that never sleeps.", "Always prepared."] },
    thinking: { glow: 0.75, fire: 0.65, lines: ["Running the play.", "Reading the tape."] },
    heavy: { glow: 1.00, fire: 1.00, lines: ["Cooking.", "This is where I live."] },
    resting: { glow: 0.22, fire: 0.22, lines: ["Even kings wait."] }
  };
  var moodEl = document.getElementById("mood");
  var frameEl = document.querySelector(".mascot-frame");
  var state = "idle", capIndex = 0;

  function rotateCaption() {
    var lines = (MOODS[state] || MOODS.idle).lines;
    if (!moodEl) return;
    moodEl.style.opacity = "0";
    setTimeout(function () { moodEl.textContent = lines[capIndex % lines.length]; moodEl.style.opacity = "1"; capIndex++; }, 260);
  }
  setInterval(rotateCaption, 5000); setTimeout(rotateCaption, 400);

  function useFallback() {
    document.body.classList.add("no3d");
    window.Mascot = { setMood: function (s) { if (MOODS[s]) state = s; }, wake: function () {} };
  }

  var canvas = document.getElementById("mascot");
  if (!window.THREE || !canvas) { useFallback(); return; }

  try {
    var THREE = window.THREE;
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    var scene = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100); camera.position.z = 3.3;
    var group = new THREE.Group(); scene.add(group);

    function radial(inner, outer) {
      var c = document.createElement("canvas"); c.width = c.height = 64;
      var g = c.getContext("2d"), grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      grd.addColorStop(0, inner); grd.addColorStop(1, outer); g.fillStyle = grd; g.fillRect(0, 0, 64, 64);
      return new THREE.CanvasTexture(c);
    }

    var glowMat = new THREE.SpriteMaterial({ map: radial("rgba(255,255,255,1)", "rgba(255,255,255,0)"), blending: THREE.AdditiveBlending, transparent: true, depthWrite: false });
    var glow = new THREE.Sprite(glowMat); glow.position.z = -0.5; glow.scale.set(3.4, 3.4, 1); group.add(glow);

    var plane = null, tex = null, vw = 2, vh = 2;
    new THREE.TextureLoader().load("assets/winner.jpg", function (t) {
      tex = t; if ("colorSpace" in t) t.colorSpace = THREE.SRGBColorSpace;
      plane = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: t, transparent: true }));
      group.add(plane); fit();
    }, undefined, function () { useFallback(); });

    // ambient embers
    var COUNT = 40, pos = new Float32Array(COUNT * 3), vel = new Float32Array(COUNT), life = new Float32Array(COUNT);
    function seed(i, fresh) {
      pos[i * 3] = (Math.random() - 0.5) * vw; pos[i * 3 + 1] = -vh / 2 - Math.random() * 0.2; pos[i * 3 + 2] = -0.15;
      vel[i] = 0.006 + Math.random() * 0.01; life[i] = fresh ? Math.random() : 1;
    }
    for (var i = 0; i < COUNT; i++) seed(i, true);
    var fgeo = new THREE.BufferGeometry(); fgeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    var fmat = new THREE.PointsMaterial({ map: radial("rgba(255,205,90,1)", "rgba(255,80,0,0)"), size: 0.2, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: .8 });
    var fire = new THREE.Points(fgeo, fmat); group.add(fire);

    var tX = 0, tY = 0;
    window.addEventListener("pointermove", function (e) { var r = canvas.getBoundingClientRect(); tX = ((e.clientX - r.left) / r.width - .5) * 2; tY = ((e.clientY - r.top) / r.height - .5) * 2; });
    window.addEventListener("deviceorientation", function (e) { if (e.gamma != null) tX = Math.max(-1, Math.min(1, e.gamma / 30)); if (e.beta != null) tY = Math.max(-1, Math.min(1, (e.beta - 45) / 30)); });

    function fit() {
      var w = canvas.clientWidth || 246, h = canvas.clientHeight || 150;
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
      vh = 2 * camera.position.z * Math.tan(camera.fov * Math.PI / 360); vw = vh * camera.aspect;
      if (plane) plane.scale.set(vw, vh, 1);
      if (tex) {
        var imgA = 720 / 1080, boxA = w / h;
        if (boxA > imgA) { tex.repeat.set(1, imgA / boxA); tex.offset.set(0, 1 - imgA / boxA); }   // top slice (crown/face)
        else { tex.repeat.set(boxA / imgA, 1); tex.offset.set((1 - boxA / imgA) / 2, 0.28); }        // center, biased up
      }
    }
    window.addEventListener("resize", fit); fit();

    var cur = { glow: .35, fire: .3 }, tgt = { glow: .35, fire: .3 }, waking = false, wakeT = 0;
    var GOLD = new THREE.Color("#ffcd3c"), GREEN = new THREE.Color("#39ff5a");
    window.Mascot = {
      setMood: function (s) { if (!MOODS[s]) return; state = s; tgt.glow = MOODS[s].glow; tgt.fire = MOODS[s].fire; },
      wake: function () { waking = true; wakeT = 0; }
    };

    var t0 = performance.now();
    function loop(now) {
      var t = (now - t0) / 1000;
      cur.glow += (tgt.glow - cur.glow) * .05; cur.fire += (tgt.fire - cur.fire) * .05;
      group.rotation.y += (tX * .22 - group.rotation.y) * .06;
      group.rotation.x += (-tY * .16 - group.rotation.x) * .06;
      group.position.y = Math.sin(t * 1.2) * .03;
      var sc = 1;
      if (waking) { wakeT = Math.min(1, wakeT + .02); sc = .4 + .6 * (1 - Math.pow(1 - wakeT, 3)); if (wakeT >= 1) waking = false; }
      group.scale.set(sc, sc, sc);
      var pulse = 1 + Math.sin(t * 2.4) * .06 * cur.glow;
      glow.scale.set(3.2 * pulse, 3.2 * pulse, 1); glowMat.opacity = (.16 + cur.glow * .5) * sc; glowMat.color.copy(GOLD).lerp(GREEN, cur.glow);
      if (frameEl) frameEl.style.setProperty("--glow", (8 + cur.glow * 22) + "px");
      for (var i = 0; i < COUNT; i++) { life[i] -= .012 * (.6 + cur.fire); pos[i * 3 + 1] += vel[i] * (.6 + cur.fire * 1.4); if (life[i] <= 0) seed(i, false); }
      fgeo.attributes.position.needsUpdate = true; fmat.opacity = (.3 + cur.fire * .5) * sc;
      renderer.render(scene, camera); requestAnimationFrame(loop);
    }
    requestAnimationFrame(loop);
  } catch (err) { useFallback(); }
})();
