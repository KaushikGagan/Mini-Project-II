// Flask remains the source of truth for OTPs and session state.
document.addEventListener("DOMContentLoaded", () => {
  const sendButton = document.querySelector("#request-otp");
  const resendButton = document.querySelector("#resend-otp");
  const emailInput = document.querySelector('input[name="email"]');
  if (!sendButton || !resendButton || !emailInput) return;

  const popup = (icon, title, text) => Swal.fire({icon, title, text, background: "#111827", color: "#fff", confirmButtonColor: "#2563eb"});
  const startCooldown = (seconds) => {
    let remaining = seconds;
    resendButton.hidden = false;
    sendButton.disabled = true;
    resendButton.disabled = true;
    const update = () => { resendButton.textContent = remaining ? `Resend OTP (${remaining}s)` : "Resend OTP"; };
    update();
    const timer = window.setInterval(() => {
      remaining -= 1;
      update();
      if (remaining <= 0) {
        window.clearInterval(timer);
        sendButton.disabled = false;
        resendButton.disabled = false;
      }
    }, 1000);
  };

  const sendOtp = async () => {
    const email = emailInput.value.trim();
    sendButton.disabled = true;
    resendButton.disabled = true;
    try {
      const response = await fetch("/auth/request-otp", {method: "POST", headers: {Accept: "application/json", "Content-Type": "application/x-www-form-urlencoded", "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content}, body: new URLSearchParams({email})});
      const data = await response.json();
      if (!response.ok) {
        await popup("error", "Unable to send OTP", data.message);
        if (data.retry_after) startCooldown(data.retry_after);
        else sendButton.disabled = false;
        return;
      }
      await popup("success", "OTP sent", data.message);
      startCooldown(data.cooldown || 60);
    } catch (_error) {
      await popup("error", "OTP request failed", "Unable to contact the server. Please try again.");
      sendButton.disabled = false;
      resendButton.disabled = false;
    }
  };
  sendButton.addEventListener("click", sendOtp);
  resendButton.addEventListener("click", sendOtp);
});
