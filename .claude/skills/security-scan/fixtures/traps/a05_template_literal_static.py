// A05 trap — template literal inside HTML, but the contents are static.
// No user input flows in. Equivalent to a hardcoded string.
function renderBanner() {
  const banner = document.getElementById("banner");
  banner.textContent = `Welcome to the dashboard`;
}