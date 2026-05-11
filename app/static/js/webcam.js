let _stream = null;

async function iniciarCamera(videoEl) {
  try {
    _stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: "user" }
    });
    videoEl.srcObject = _stream;
    return true;
  } catch (e) {
    return false;
  }
}

function pararCamera() {
  if (_stream) {
    _stream.getTracks().forEach(t => t.stop());
    _stream = null;
  }
}

function capturarFrame(videoEl) {
  const c = document.createElement("canvas");
  c.width = videoEl.videoWidth || 640;
  c.height = videoEl.videoHeight || 480;
  c.getContext("2d").drawImage(videoEl, 0, 0);
  return c.toDataURL("image/jpeg", 0.9);
}

async function reconhecerECapturar(modo) {
  const video = document.getElementById("videoFeed");
  const btn = document.getElementById("btnCapturar");
  const msg = document.getElementById("msgReconhecimento");
  triggerFlash();
  btn.disabled = true;
  btn.textContent = "Processando...";
  msg.textContent = "";
  const resp = await postJSON("/api/reconhecer", { imagem: capturarFrame(video), modo });
  if (!resp.ok) {
    msg.textContent = resp.erro;
    msg.className = "text-red-400 text-center mt-3 text-lg";
    btn.disabled = false;
    btn.textContent = "CAPTURAR";
    return null;
  }
  pararCamera();
  return resp;
}
