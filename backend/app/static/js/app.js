// Progressive enhancement only: Flask remains the source of truth for OTPs and sessions.
document.addEventListener("DOMContentLoaded", () => {
  const requestOtpButton = document.querySelector("#request-otp");
  const emailInput = document.querySelector('input[name="email"]');

  if (!requestOtpButton || !emailInput) return;

  requestOtpButton.addEventListener("click", async () => {
    const email = emailInput.value.trim();
    requestOtpButton.disabled = true;
    requestOtpButton.textContent = "Generating…";

    try {
      const response = await fetch("/auth/request-otp", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({ email }),
      });
      const data = await response.json();
      await Swal.fire({
        icon: data.ok ? "success" : "error",
        title: data.ok ? "OTP generated" : "Email required",
        text: data.message,
        background: "#111827",
        color: "#fff",
        confirmButtonColor: "#2563eb",
      });
    } catch (_error) {
      await Swal.fire({
        icon: "error",
        title: "OTP request failed",
        text: "Unable to contact the server. Please try again.",
        background: "#111827",
        color: "#fff",
        confirmButtonColor: "#2563eb",
      });
    } finally {
      requestOtpButton.disabled = false;
      requestOtpButton.textContent = "Request OTP";
    }
  });
});
