const recentList = document.getElementById("recent-list");
const filtersContent = document.getElementById("filters-content");
const filtersPanel = document.getElementById("filters-panel");
const docContent = document.getElementById("doc-content");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results");
const refreshTreeButton = document.getElementById("refresh-tree");
const helpButton = document.getElementById("help-button");
const helpModal = document.getElementById("help-modal");
const helpClose = document.getElementById("help-close");
const authButton = document.getElementById("auth-button");
const authMenu = document.getElementById("auth-menu");
const authModal = document.getElementById("auth-modal");
const authClose = document.getElementById("auth-close");
const authMethodTabs = Array.from(document.querySelectorAll(".auth-method-tab"));
const authMethodViews = Array.from(document.querySelectorAll(".auth-method-view"));
const authPasswordSubmit = document.getElementById("auth-password-submit");
const authSmsSend = document.getElementById("auth-sms-send");
const authSmsVerify = document.getElementById("auth-sms-verify");
const authQrRefresh = document.getElementById("auth-qr-refresh");
const authQrConfirm = document.getElementById("auth-qr-confirm");
const authFeedback = document.getElementById("auth-feedback");
const loginInput = document.getElementById("login-value");
const passwordInput = document.getElementById("password-value");
const phoneInput = document.getElementById("phone-value");
const smsCodeInput = document.getElementById("sms-code-value");
const qrImage = document.getElementById("qr-image");
const qrFallback = document.getElementById("qr-fallback");
const registerModal = document.getElementById("register-modal");
const registerClose = document.getElementById("register-close");
const registerLogin = document.getElementById("register-login");
const registerPassword = document.getElementById("register-password");
const registerContactMode = document.getElementById("register-contact-mode");
const registerPhone = document.getElementById("register-phone");
const registerEmail = document.getElementById("register-email");
const registerEmailLabel = document.getElementById("register-email-label");
const registerValidateButton = document.getElementById("register-validate");
const registerSendCodeButton = document.getElementById("register-send-code");
const registerConfirmButton = document.getElementById("register-confirm");
const registerCodeInput = document.getElementById("register-code");
const registerFeedback = document.getElementById("register-feedback");
const tabButtons = Array.from(document.querySelectorAll(".tab-button[data-tab]"));

const tabViews = {
  home: document.getElementById("home-view"),
  library: document.getElementById("library-view"),
  glossary: document.getElementById("glossary-view"),
  "my-collection": document.getElementById("collection-view"),
  "my-doc": document.getElementById("mydoc-view"),
};

const DEFAULT_TAB = "library";
const AUTH_USER_STORAGE_KEY = "otd.authUser";
const AUTH_IDLE_TIMEOUT_MS = 30 * 60 * 1000;
let currentQrSessionId = null;
let qrPollTimer = null;
let currentRegistrationChallengeId = null;
let authIdleTimer = null;

function setAuthenticatedUser(displayName) {
  if (!authButton) {
    return;
  }
  const normalizedName = (displayName || "").trim();
  const isAuthenticated = Boolean(normalizedName);
  if (normalizedName) {
    authButton.textContent = normalizedName;
    authButton.setAttribute("aria-label", `Профиль пользователя: ${normalizedName}`);
    window.localStorage.setItem(AUTH_USER_STORAGE_KEY, normalizedName);
  } else {
    authButton.textContent = "Вход";
    authButton.setAttribute("aria-label", "Вход");
    window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);
  }

  if (authMenu) {
    authMenu.querySelectorAll('[data-auth-action="login"], [data-auth-action="register"]').forEach((item) => {
      item.classList.toggle("is-hidden", isAuthenticated);
    });
    authMenu.querySelectorAll('[data-auth-action="logout"]').forEach((item) => {
      item.classList.toggle("is-hidden", !isAuthenticated);
    });
  }

  if (isAuthenticated) {
    resetAuthIdleTimer();
  } else {
    clearAuthIdleTimer();
  }
}

function restoreAuthenticatedUser() {
  const savedName = window.localStorage.getItem(AUTH_USER_STORAGE_KEY);
  if (savedName) {
    setAuthenticatedUser(savedName);
  }
}

function normalizeHashTab(hashValue) {
  const normalized = (hashValue || "").replace(/^#/, "").trim().toLowerCase();
  if (normalized && tabViews[normalized]) {
    return normalized;
  }
  return DEFAULT_TAB;
}

function clearAuthIdleTimer() {
  if (authIdleTimer) {
    clearTimeout(authIdleTimer);
    authIdleTimer = null;
  }
}

function handleAuthTimeout() {
  if (!window.localStorage.getItem(AUTH_USER_STORAGE_KEY)) {
    clearAuthIdleTimer();
    return;
  }
  setAuthenticatedUser("");
  closeAuthMenu();
  closeAuthModal();
  closeRegisterModal();
  stopQrPolling();
  setAuthFeedback("Сеанс завершен из-за неактивности. Выполните вход еще раз.", "neutral");
}

function resetAuthIdleTimer() {
  clearAuthIdleTimer();
  if (!window.localStorage.getItem(AUTH_USER_STORAGE_KEY)) {
    return;
  }
  authIdleTimer = window.setTimeout(handleAuthTimeout, AUTH_IDLE_TIMEOUT_MS);
}

function handleLogout() {
  setAuthenticatedUser("");
  closeAuthMenu();
  closeAuthModal();
  closeRegisterModal();
  stopQrPolling();
  setAuthFeedback("Вы вышли из программы.", "neutral");
}

function recordAuthActivity() {
  if (window.localStorage.getItem(AUTH_USER_STORAGE_KEY)) {
    resetAuthIdleTimer();
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail || `Request failed: ${response.status}`;
    throw new Error(detail);
  }
  return body;
}

async function loadDocument(docId) {
  setActiveTab("library");
  const documentData = await fetchJson(`/api/v1/documents/${docId}`);
  docContent.classList.remove("empty-state");
  const parts = [
    `Title: ${documentData.title}`,
    `Product: ${documentData.metadata.product || "-"}`,
    `Vendor: ${documentData.metadata.vendor || "-"}`,
    `Domain: ${documentData.metadata.domain || "-"}`,
    `Release: ${documentData.metadata.release || "-"}`,
    "",
    ...documentData.chunks.map((chunk) => chunk.content),
  ];
  docContent.textContent = parts.join("\n");
}

function buildRecentItem(topic) {
  const item = document.createElement("li");
  const icon = document.createElement("span");
  icon.textContent = "▣";
  const button = document.createElement("button");
  button.className = "recent-open";
  button.type = "button";
  button.textContent = topic.title;
  button.addEventListener("click", () => loadDocument(topic.doc_id));
  item.appendChild(icon);
  item.appendChild(button);
  return item;
}

function buildResultButton(hit) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Открыть документ";
  button.addEventListener("click", () => loadDocument(hit.doc_id));
  return button;
}

function renderFilters(products) {
  const productNames = products.map((product) => product.name);
  const releaseNames = products.flatMap((product) => product.releases.map((release) => release.name));

  const productSummary = filtersContent.querySelector("details:nth-of-type(1) summary span");
  const releaseSummary = filtersContent.querySelector("details:nth-of-type(2) summary span");
  const domainSummary = filtersContent.querySelector("details:nth-of-type(3) summary span");

  if (productSummary) {
    productSummary.textContent = productNames.length ? `(${productNames.length})` : "(all)";
  }
  if (releaseSummary) {
    releaseSummary.textContent = releaseNames.length ? `(${releaseNames.length})` : "(all)";
  }
  if (domainSummary) {
    const domains = products.flatMap((product) =>
      product.releases.flatMap((release) => release.domains.map((domain) => domain.name))
    );
    domainSummary.textContent = domains.length ? `(${new Set(domains).size})` : "(all)";
  }
}

function renderTree(products) {
  recentList.innerHTML = "";
  const topics = products.flatMap((product) =>
    product.releases.flatMap((release) => release.domains.flatMap((domain) => domain.topics))
  );

  renderFilters(products);

  const recentTopics = topics.slice(0, 8);
  if (!recentTopics.length) {
    recentList.innerHTML = '<li class="empty-state">Библиотеки пока не загружены.</li>';
    return;
  }

  recentTopics.forEach((topic) => recentList.appendChild(buildRecentItem(topic)));
}

async function loadTree() {
  try {
    const treeData = await fetchJson("/api/v1/documents/tree");
    renderTree(treeData.products);
  } catch (error) {
    recentList.innerHTML = `<li class="empty-state">Не удалось загрузить библиотеку: ${error.message}</li>`;
  }
}

function renderSearchResults(payload) {
  searchResults.innerHTML = "";
  if (!payload.hits.length) {
    searchResults.classList.add("empty-state");
    searchResults.textContent = "Совпадений не найдено.";
    return;
  }

  searchResults.classList.remove("empty-state");
  payload.hits.forEach((hit) => {
    const card = document.createElement("article");
    card.className = "search-result";
    card.innerHTML = `
      <h3>${hit.title}</h3>
      <p>${hit.snippet}</p>
      <small>Вендор: ${hit.vendor || "-"} | Домен: ${hit.domain || "-"} | Релиз: ${hit.release || "-"}</small>
    `;
    card.appendChild(buildResultButton(hit));
    searchResults.appendChild(card);
  });
}

async function handleSearch(event) {
  event.preventDefault();
  setActiveTab("library");
  const query = searchInput.value.trim();
  if (!query) {
    return;
  }

  const payload = await fetchJson("/api/v1/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, page: 1, size: 10, filters: {} }),
  });
  renderSearchResults(payload);
}

function setActiveTab(tabKey, options = {}) {
  const { updateHash = true } = options;
  const resolvedTab = tabViews[tabKey] ? tabKey : DEFAULT_TAB;

  tabButtons.forEach((button) => {
    const isActive = button.dataset.tab === resolvedTab;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  Object.entries(tabViews).forEach(([key, view]) => {
    if (!view) {
      return;
    }
    view.classList.toggle("is-hidden", key !== resolvedTab);
  });

  if (filtersPanel) {
    filtersPanel.classList.toggle("is-hidden", resolvedTab !== "library");
  }

  if (updateHash) {
    const nextHash = `#${resolvedTab}`;
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash;
    }
  }
}

tabButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const tabKey = button.dataset.tab;
    if (!tabKey || !tabViews[tabKey]) {
      return;
    }
    setActiveTab(tabKey);
  });
});

function openHelpModal() {
  if (!helpModal) {
    return;
  }
  helpModal.classList.remove("is-hidden");
}

function closeHelpModal() {
  if (!helpModal) {
    return;
  }
  helpModal.classList.add("is-hidden");
}

function openAuthMenu() {
  if (!authMenu || !authButton) {
    return;
  }
  authMenu.classList.remove("is-hidden");
  authButton.setAttribute("aria-expanded", "true");
}

function closeAuthMenu() {
  if (!authMenu || !authButton) {
    return;
  }
  authMenu.classList.add("is-hidden");
  authButton.setAttribute("aria-expanded", "false");
}

function toggleAuthMenu() {
  if (!authMenu || authMenu.classList.contains("is-hidden")) {
    openAuthMenu();
  } else {
    closeAuthMenu();
  }
}

function openAuthModal() {
  if (!authModal) {
    return;
  }
  authModal.classList.remove("is-hidden");
}

function closeAuthModal() {
  if (!authModal) {
    return;
  }
  authModal.classList.add("is-hidden");
  stopQrPolling();
}

function openRegisterModal() {
  if (!registerModal) {
    return;
  }
  registerModal.classList.remove("is-hidden");
}

function closeRegisterModal() {
  if (!registerModal) {
    return;
  }
  registerModal.classList.add("is-hidden");
}

function setRegisterFeedback(message, kind = "neutral") {
  if (!registerFeedback) {
    return;
  }
  registerFeedback.textContent = message;
  registerFeedback.classList.remove("is-error", "is-success", "empty-state");
  if (kind === "error") {
    registerFeedback.classList.add("is-error");
  } else if (kind === "success") {
    registerFeedback.classList.add("is-success");
  } else {
    registerFeedback.classList.add("empty-state");
  }
}

function updateRegisterContactFields() {
  if (!registerContactMode || !registerPhone || !registerEmail || !registerEmailLabel) {
    return;
  }
  const isPhone = registerContactMode.value === "phone";
  registerPhone.classList.toggle("is-hidden", !isPhone);
  registerEmail.classList.toggle("is-hidden", isPhone);
  registerEmailLabel.classList.toggle("is-hidden", isPhone);
}

function getRegistrationPayload() {
  const login = (registerLogin?.value || "").trim();
  const password = registerPassword?.value || "";
  const mode = registerContactMode?.value || "phone";
  const phone = mode === "phone" ? (registerPhone?.value || "").trim() : null;
  const email = mode === "email" ? (registerEmail?.value || "").trim() : null;
  return { login, password, phone, email };
}

async function validateRegistration() {
  try {
    const payload = getRegistrationPayload();
    const response = await postJson("/api/v1/auth/register/validate", payload);
    if (!response.valid) {
      setRegisterFeedback(response.errors.join("; "), "error");
      return false;
    }
    setRegisterFeedback("Данные корректны. Можно отправлять код подтверждения.", "success");
    return true;
  } catch (error) {
    setRegisterFeedback(error.message, "error");
    return false;
  }
}

async function startRegistration() {
  const valid = await validateRegistration();
  if (!valid) {
    return;
  }
  try {
    const payload = getRegistrationPayload();
    const response = await postJson("/api/v1/auth/register/start", payload);
    currentRegistrationChallengeId = response.challenge_id;
    const demoCode = response.demo_code ? ` Демо-код: ${response.demo_code}.` : "";
    setRegisterFeedback(`Код отправлен на ${response.contact_masked}.${demoCode}`, "success");
  } catch (error) {
    setRegisterFeedback(error.message, "error");
  }
}

async function confirmRegistration() {
  const code = (registerCodeInput?.value || "").trim();
  if (!currentRegistrationChallengeId) {
    setRegisterFeedback("Сначала запросите код подтверждения.", "error");
    return;
  }
  if (!code) {
    setRegisterFeedback("Введите код подтверждения.", "error");
    return;
  }
  try {
    const payload = await postJson("/api/v1/auth/register/confirm", {
      challenge_id: currentRegistrationChallengeId,
      code,
    });
    setAuthenticatedUser(payload.display_name || getRegistrationPayload().login);
    currentRegistrationChallengeId = null;
    setRegisterFeedback("Регистрация завершена. Теперь вы можете войти в программу.", "success");
  } catch (error) {
    setRegisterFeedback(error.message, "error");
  }
}

function setAuthFeedback(message, kind = "neutral") {
  if (!authFeedback) {
    return;
  }
  authFeedback.textContent = message;
  authFeedback.classList.remove("is-error", "is-success", "empty-state");
  if (kind === "error") {
    authFeedback.classList.add("is-error");
  } else if (kind === "success") {
    authFeedback.classList.add("is-success");
  } else {
    authFeedback.classList.add("empty-state");
  }
}

function stopQrPolling() {
  if (qrPollTimer) {
    clearInterval(qrPollTimer);
    qrPollTimer = null;
  }
}

async function checkQrStatus() {
  if (!currentQrSessionId) {
    return;
  }
  try {
    const statusPayload = await fetchJson(`/api/v1/auth/qr/status/${currentQrSessionId}`);
    if (statusPayload.status === "confirmed") {
      setAuthFeedback("Вход по QR подтвержден. Авторизация успешна.", "success");
      stopQrPolling();
      return;
    }
    if (statusPayload.status === "expired") {
      setAuthFeedback("QR-сессия истекла. Обновите QR код.", "error");
      stopQrPolling();
      return;
    }
    setAuthFeedback("Ожидаем сканирование QR Code...", "neutral");
  } catch (error) {
    setAuthFeedback(error.message, "error");
    stopQrPolling();
  }
}

async function startQrFlow() {
  stopQrPolling();
  try {
    const qrPayload = await postJson("/api/v1/auth/qr/create", {});
    currentQrSessionId = qrPayload.session_id;
    if (qrImage) {
      qrImage.src = qrPayload.qr_image_data_url;
      qrImage.classList.remove("is-hidden");
    }
    if (qrFallback) {
      qrFallback.classList.add("is-hidden");
    }
    setAuthFeedback("QR Code создан. Отсканируйте его в мобильном приложении.", "neutral");
    qrPollTimer = setInterval(checkQrStatus, 3000);
  } catch (error) {
    setAuthFeedback(error.message, "error");
  }
}

async function submitPasswordLogin() {
  const login = (loginInput?.value || "").trim();
  const password = passwordInput?.value || "";
  if (!login || !password) {
    setAuthFeedback("Введите логин и пароль.", "error");
    return;
  }
  try {
    const payload = await postJson("/api/v1/auth/login/password", { login, password });
    setAuthenticatedUser(payload.display_name || login);
    setAuthFeedback(`Успешный вход: ${payload.display_name || "Пользователь"}.`, "success");
    closeAuthMenu();
    closeAuthModal();
  } catch (error) {
    setAuthFeedback(error.message, "error");
  }
}

function handlePasswordEnterKey(event) {
  if (event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  submitPasswordLogin();
}

async function sendSmsCode() {
  const phone = (phoneInput?.value || "").trim();
  if (!phone) {
    setAuthFeedback("Введите номер телефона для СМС.", "error");
    return;
  }
  try {
    const payload = await postJson("/api/v1/auth/sms/send-code", { phone });
    const demoCode = payload.demo_code ? ` Демо-код: ${payload.demo_code}.` : "";
    setAuthFeedback(`Код отправлен на ${payload.phone_masked}.${demoCode}`, "success");
  } catch (error) {
    setAuthFeedback(error.message, "error");
  }
}

async function verifySmsCode() {
  const phone = (phoneInput?.value || "").trim();
  const code = (smsCodeInput?.value || "").trim();
  if (!phone || !code) {
    setAuthFeedback("Введите номер телефона и код из СМС.", "error");
    return;
  }
  try {
    const payload = await postJson("/api/v1/auth/sms/verify", { phone, code });
    setAuthenticatedUser(payload.display_name || "Пользователь");
    setAuthFeedback("Код подтвержден. Вход выполнен успешно.", "success");
  } catch (error) {
    setAuthFeedback(error.message, "error");
  }
}

async function confirmQrScan() {
  if (!currentQrSessionId) {
    setAuthFeedback("Сначала обновите QR Code.", "error");
    return;
  }
  try {
    const payload = await postJson("/api/v1/auth/qr/confirm", { session_id: currentQrSessionId });
    setAuthenticatedUser(payload.display_name || "Пользователь");
    await checkQrStatus();
  } catch (error) {
    setAuthFeedback(error.message, "error");
  }
}

function setAuthMethod(methodKey) {
  stopQrPolling();

  authMethodTabs.forEach((tab) => {
    const isActive = tab.dataset.authMethod === methodKey;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", isActive ? "true" : "false");
  });

  authMethodViews.forEach((view) => {
    const isActive = view.dataset.authView === methodKey;
    view.classList.toggle("is-hidden", !isActive);
  });

  if (methodKey === "password") {
    setAuthFeedback("Введите логин и пароль для входа.", "neutral");
  }
  if (methodKey === "sms") {
    setAuthFeedback("Запросите код из СМС и подтвердите его.", "neutral");
  }
  if (methodKey === "qr") {
    startQrFlow();
  }
}

if (helpButton) {
  helpButton.addEventListener("click", openHelpModal);
}

if (authButton) {
  authButton.addEventListener("click", toggleAuthMenu);
}

if (authMenu) {
  authMenu.addEventListener("click", (event) => {
    const menuItem = event.target.closest(".auth-menu-item");
    if (!menuItem) {
      return;
    }
    const action = menuItem.dataset.authAction;
    if (action === "login") {
      openAuthModal();
      setAuthMethod("password");
    }
    if (action === "register") {
      openRegisterModal();
      updateRegisterContactFields();
      setRegisterFeedback("Заполните форму для регистрации нового пользователя.", "neutral");
    }
    if (action === "logout") {
      handleLogout();
    }
    closeAuthMenu();
  });
}

if (registerContactMode) {
  registerContactMode.addEventListener("change", updateRegisterContactFields);
}

if (registerValidateButton) {
  registerValidateButton.addEventListener("click", validateRegistration);
}

if (registerSendCodeButton) {
  registerSendCodeButton.addEventListener("click", startRegistration);
}

if (registerConfirmButton) {
  registerConfirmButton.addEventListener("click", confirmRegistration);
}

if (registerClose) {
  registerClose.addEventListener("click", closeRegisterModal);
}

if (registerModal) {
  registerModal.addEventListener("click", (event) => {
    if (event.target === registerModal) {
      closeRegisterModal();
    }
  });
}

if (authPasswordSubmit) {
  authPasswordSubmit.addEventListener("click", submitPasswordLogin);
}

if (loginInput) {
  loginInput.addEventListener("keydown", handlePasswordEnterKey);
}

if (passwordInput) {
  passwordInput.addEventListener("keydown", handlePasswordEnterKey);
}

if (authSmsSend) {
  authSmsSend.addEventListener("click", sendSmsCode);
}

if (authSmsVerify) {
  authSmsVerify.addEventListener("click", verifySmsCode);
}

if (authQrRefresh) {
  authQrRefresh.addEventListener("click", startQrFlow);
}

if (authQrConfirm) {
  authQrConfirm.addEventListener("click", confirmQrScan);
}

if (authClose) {
  authClose.addEventListener("click", closeAuthModal);
}

if (authModal) {
  authModal.addEventListener("click", (event) => {
    if (event.target === authModal) {
      closeAuthModal();
    }
  });
}

authMethodTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const method = tab.dataset.authMethod;
    if (method) {
      setAuthMethod(method);
    }
  });
});

if (helpClose) {
  helpClose.addEventListener("click", closeHelpModal);
}

if (helpModal) {
  helpModal.addEventListener("click", (event) => {
    if (event.target === helpModal) {
      closeHelpModal();
    }
  });
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && helpModal && !helpModal.classList.contains("is-hidden")) {
    closeHelpModal();
  }
  if (event.key === "Escape" && authMenu && !authMenu.classList.contains("is-hidden")) {
    closeAuthMenu();
  }
  if (event.key === "Escape" && authModal && !authModal.classList.contains("is-hidden")) {
    closeAuthModal();
  }
  if (event.key === "Escape" && registerModal && !registerModal.classList.contains("is-hidden")) {
    closeRegisterModal();
  }
});

["click", "keydown", "mousemove", "mousedown", "scroll", "touchstart", "focusin", "input"].forEach((eventName) => {
  document.addEventListener(eventName, recordAuthActivity, true);
});

document.addEventListener("click", (event) => {
  if (!authMenu || !authButton) {
    return;
  }
  if (event.target === authButton || authButton.contains(event.target) || authMenu.contains(event.target)) {
    return;
  }
  closeAuthMenu();
});

window.addEventListener("hashchange", () => {
  const tabFromHash = normalizeHashTab(window.location.hash);
  setActiveTab(tabFromHash, { updateHash: false });
});

searchForm.addEventListener("submit", handleSearch);
refreshTreeButton.addEventListener("click", loadTree);

setActiveTab(normalizeHashTab(window.location.hash), { updateHash: false });

if (!window.location.hash || !tabViews[normalizeHashTab(window.location.hash)]) {
  window.location.hash = `#${DEFAULT_TAB}`;
}

restoreAuthenticatedUser();
updateRegisterContactFields();
loadTree();