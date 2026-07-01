const recentList = document.getElementById("recent-list");
const filtersContent = document.getElementById("filters-content");
const filtersPanel = document.getElementById("filters-panel");
const filtersResetButton = document.getElementById("filters-reset");
const docContent = document.getElementById("doc-content");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results");
const searchSuggestions = document.getElementById("search-suggestions");
const refreshTreeButton = document.getElementById("refresh-tree");
const glossarySearchInput = document.getElementById("glossary-search");
const glossaryAdminTabButton = document.getElementById("glossary-admin-tab");
const glossaryLanguageSelect = document.getElementById("glossary-language");
const glossarySortSelect = document.getElementById("glossary-sort");
const glossaryList = document.getElementById("glossary-list");
const glossaryDetails = document.getElementById("glossary-details");
const glossaryAdminPanel = document.getElementById("glossary-admin-panel");
const glossaryAdminAbbrInput = document.getElementById("glossary-admin-abbr");
const glossaryAdminRelatedInput = document.getElementById("glossary-admin-related");
const glossaryAdminTermRuInput = document.getElementById("glossary-admin-term-ru");
const glossaryAdminTermEnInput = document.getElementById("glossary-admin-term-en");
const glossaryAdminDefinitionRuInput = document.getElementById("glossary-admin-definition-ru");
const glossaryAdminDefinitionEnInput = document.getElementById("glossary-admin-definition-en");
const glossaryAdminKeywordsInput = document.getElementById("glossary-admin-keywords");
const glossaryAdminSourcesList = document.getElementById("glossary-admin-sources-list");
const glossaryAdminAddSourceButton = document.getElementById("glossary-admin-add-source");
const glossaryAdminSearchInput = document.getElementById("glossary-admin-search");
const glossaryAdminImportFileInput = document.getElementById("glossary-admin-import-file");
const glossaryAdminTemplateButton = document.getElementById("glossary-admin-template");
const glossaryAdminImportButton = document.getElementById("glossary-admin-import");
const glossaryAdminExportButton = document.getElementById("glossary-admin-export");
const glossaryAdminList = document.getElementById("glossary-admin-list");
const glossaryAdminPrevButton = document.getElementById("glossary-admin-prev");
const glossaryAdminNextButton = document.getElementById("glossary-admin-next");
const glossaryAdminPageStatus = document.getElementById("glossary-admin-page-status");
const glossaryAdminAuditRefreshButton = document.getElementById("glossary-admin-audit-refresh");
const glossaryAdminAuditList = document.getElementById("glossary-admin-audit-list");
const glossaryAdminNewButton = document.getElementById("glossary-admin-new");
const glossaryAdminSaveButton = document.getElementById("glossary-admin-save");
const glossaryAdminDeleteButton = document.getElementById("glossary-admin-delete");
const glossaryAdminFeedback = document.getElementById("glossary-admin-feedback");
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
const aiHomeQuestionInput = document.getElementById("ai-home-question");
const aiHomeModeInput = document.getElementById("ai-home-mode");
const aiHomeSourceInput = document.getElementById("ai-home-source");
const aiHomeMaxCitationsInput = document.getElementById("ai-home-max-citations");
const aiHomeUseCurrentDocInput = document.getElementById("ai-home-use-current-doc");
const aiHomeSubmitButton = document.getElementById("ai-home-submit");
const aiHomeStatus = document.getElementById("ai-home-status");
const aiHomeAnswer = document.getElementById("ai-home-answer");
const aiHomeCitationsList = document.getElementById("ai-home-citations-list");
const tabButtons = Array.from(document.querySelectorAll(".tab-button[data-tab]"));

const tabViews = {
  home: document.getElementById("home-view"),
  library: document.getElementById("library-view"),
  glossary: document.getElementById("glossary-view"),
  "glossary-admin": document.getElementById("glossary-admin-view"),
  "my-collection": document.getElementById("collection-view"),
  "my-doc": document.getElementById("mydoc-view"),
};

const DEFAULT_TAB = "library";
const AUTH_USER_STORAGE_KEY = "otd.authUser";
const AUTH_TOKEN_STORAGE_KEY = "otd.authToken";
const AUTH_ROLE_STORAGE_KEY = "otd.authRole";
const AUTH_IDLE_TIMEOUT_MS = 30 * 60 * 1000;
let currentQrSessionId = null;
let qrPollTimer = null;
let currentRegistrationChallengeId = null;
let authIdleTimer = null;
let currentOpenedDocId = null;
let libraryTopics = [];
let lastSearchQuery = "";
let activeGlossaryAbbr = null;
let glossaryLanguage = "ru";
let glossarySortMode = "abbr";
let glossaryEntries = [];
let glossaryLoaded = false;
let glossaryEditingOriginalAbbr = null;
let glossaryAdminFilter = "";
let glossaryAdminPage = 1;
const GLOSSARY_ADMIN_PAGE_SIZE = 8;
const activeLibraryFilters = {
  node_type: new Set(),
  release: new Set(),
  product: new Set(),
};

const LIBRARY_FILTER_CONFIG = [
  { field: "node_type", detailIndex: 1 },
  { field: "release", detailIndex: 2 },
  { field: "product", detailIndex: 3 },
];

const GLOSSARY_ENTRIES = [
  {
    abbr: "AMF",
    termEn: "Access and Mobility Management Function",
    termRu: "Функция управления доступом и мобильностью",
    definition: "Управляет регистрацией UE, мобильностью и взаимодействием в контрольной плоскости 5G Core.",
    related: ["SMF", "AUSF", "gNB"],
    keywords: ["amf", "mobility"],
  },
  {
    abbr: "AUSF",
    termEn: "Authentication Server Function",
    termRu: "Функция сервера аутентификации",
    definition: "Отвечает за аутентификацию абонента и проверку учетных данных в 5G Core.",
    related: ["AMF", "UDM"],
    keywords: ["ausf", "auth"],
  },
  {
    abbr: "EPC",
    termEn: "Evolved Packet Core",
    termRu: "Ядро пакетной сети LTE",
    definition: "Архитектура ядра LTE, обеспечивающая управление сеансами, мобильностью и доступом к пакетной сети.",
    related: ["MME", "SGW", "PGW"],
    keywords: ["epc", "lte core"],
  },
  {
    abbr: "gNB",
    termEn: "Next Generation NodeB",
    termRu: "Базовая станция 5G",
    definition: "Радиодоступ 5G NR, обеспечивающий интерфейсы N2/N3 к ядру 5G.",
    related: ["AMF", "UPF", "RAN"],
    keywords: ["gnb", "radio"],
  },
  {
    abbr: "HSS",
    termEn: "Home Subscriber Server",
    termRu: "Домашний сервер абонентов",
    definition: "Хранилище профилей абонентов и параметров аутентификации в EPC.",
    related: ["MME", "PCRF"],
    keywords: ["hss", "subscriber"],
  },
  {
    abbr: "MME",
    termEn: "Mobility Management Entity",
    termRu: "Узел управления мобильностью (LTE)",
    definition: "Основной узел контроля мобильности и сигнализации NAS в EPC.",
    related: ["EPC", "HSS", "SGW"],
    keywords: ["mme", "mobility"],
  },
  {
    abbr: "NRF",
    termEn: "Network Repository Function",
    termRu: "Репозиторий сетевых функций",
    definition: "Каталог и сервис-дискавери сетевых функций в сервис-ориентированной архитектуре 5G.",
    related: ["AMF", "SMF", "PCF"],
    keywords: ["nrf", "repository"],
  },
  {
    abbr: "NSSF",
    termEn: "Network Slice Selection Function",
    termRu: "Функция выбора сетевого среза",
    definition: "Подбирает подходящий сетевой срез в зависимости от профиля и запроса абонента.",
    related: ["AMF", "SMF"],
    keywords: ["nssf", "slice"],
  },
  {
    abbr: "PCF",
    termEn: "Policy Control Function",
    termRu: "Функция управления политиками",
    definition: "Формирует policy-решения для QoS, charging и маршрутизации в 5G.",
    related: ["SMF", "UDR"],
    keywords: ["pcf", "policy"],
  },
  {
    abbr: "PCRF",
    termEn: "Policy and Charging Rules Function",
    termRu: "Функция правил политик и тарификации",
    definition: "Управляет правилами QoS и тарификации в EPC.",
    related: ["PGW", "HSS"],
    keywords: ["pcrf", "charging"],
  },
  {
    abbr: "PGW",
    termEn: "Packet Data Network Gateway",
    termRu: "Шлюз к пакетной сети данных",
    definition: "Обеспечивает выход абонентского трафика EPC во внешние IP-сети.",
    related: ["SGW", "PCRF"],
    keywords: ["pgw", "gateway"],
  },
  {
    abbr: "RAN",
    termEn: "Radio Access Network",
    termRu: "Сеть радиодоступа",
    definition: "Радиочасть сети, включающая базовые станции и интерфейсы доступа UE.",
    related: ["gNB", "UE"],
    keywords: ["ran", "radio"],
  },
  {
    abbr: "SGW",
    termEn: "Serving Gateway",
    termRu: "Обслуживающий шлюз",
    definition: "Якорь пользовательской плоскости между eNodeB/gNB и PGW в EPC.",
    related: ["MME", "PGW"],
    keywords: ["sgw", "serving gateway"],
  },
  {
    abbr: "SMF",
    termEn: "Session Management Function",
    termRu: "Функция управления сессиями",
    definition: "Управляет PDU-сессиями, адресацией UE и взаимодействием с UPF.",
    related: ["AMF", "UPF", "PCF"],
    keywords: ["smf", "session"],
  },
  {
    abbr: "UDM",
    termEn: "Unified Data Management",
    termRu: "Унифицированное управление данными",
    definition: "Управляет данными абонента и параметрами подписки в 5G.",
    related: ["AUSF", "UDR"],
    keywords: ["udm", "subscriber"],
  },
  {
    abbr: "UDR",
    termEn: "Unified Data Repository",
    termRu: "Унифицированное хранилище данных",
    definition: "Централизованное хранилище профилей, политик и параметров подписки.",
    related: ["UDM", "PCF"],
    keywords: ["udr", "repository"],
  },
  {
    abbr: "UE",
    termEn: "User Equipment",
    termRu: "Пользовательское оборудование",
    definition: "Конечное устройство абонента, которое регистрируется в сети и передает трафик.",
    related: ["RAN", "AMF"],
    keywords: ["ue", "device"],
  },
  {
    abbr: "UPF",
    termEn: "User Plane Function",
    termRu: "Функция пользовательской плоскости",
    definition: "Обрабатывает пользовательский трафик, маршрутизацию и применение правил QoS в 5G.",
    related: ["SMF", "gNB"],
    keywords: ["upf", "user plane"],
  },
].sort((left, right) => left.abbr.localeCompare(right.abbr, "en"));

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;");
}

function normalizeGlossaryEntry(rawEntry) {
  return {
    abbr: rawEntry.abbr,
    termRu: rawEntry.term_ru || rawEntry.termRu || "",
    termEn: rawEntry.term_en || rawEntry.termEn || "",
    definitionRu: rawEntry.definition_ru || rawEntry.definitionRu || rawEntry.definition || "",
    definitionEn: rawEntry.definition_en || rawEntry.definitionEn || rawEntry.definition || "",
    related: Array.isArray(rawEntry.related) ? rawEntry.related : [],
    keywords: Array.isArray(rawEntry.keywords) ? rawEntry.keywords : [],
    manualSources: Array.isArray(rawEntry.manual_sources) ? rawEntry.manual_sources : [],
  };
}

async function loadGlossaryEntries() {
  try {
    const payload = await fetchJson("/api/v1/glossary");
    glossaryEntries = Array.isArray(payload)
      ? payload.map(normalizeGlossaryEntry).filter((entry) => entry.abbr)
      : [];
  } catch {
    glossaryEntries = GLOSSARY_ENTRIES.map((entry) => ({
      ...entry,
      definitionRu: entry.definition,
      definitionEn: entry.definition,
      manualSources: [],
    }));
  } finally {
    glossaryLoaded = true;
    renderGlossaryList(glossarySearchInput?.value || "");
    renderGlossaryAdminList();
  }
}

function getGlossaryTerm(entry) {
  if (glossaryLanguage === "en") {
    return entry.termEn || entry.termRu;
  }
  return entry.termRu || entry.termEn;
}

function getGlossarySecondaryTerm(entry) {
  if (glossaryLanguage === "en") {
    return entry.termRu || "";
  }
  return entry.termEn || "";
}

function getGlossaryDefinition(entry) {
  if (glossaryLanguage === "en") {
    return entry.definitionEn || entry.definitionRu;
  }
  return entry.definitionRu || entry.definitionEn;
}

function sortGlossaryEntries(entries) {
  const items = [...entries];
  items.sort((left, right) => {
    if (glossarySortMode === "ru") {
      return (left.termRu || "").localeCompare(right.termRu || "", "ru");
    }
    if (glossarySortMode === "en") {
      return (left.termEn || "").localeCompare(right.termEn || "", "en");
    }
    return (left.abbr || "").localeCompare(right.abbr || "", "en");
  });
  return items;
}

function resolveGlossaryManualSource(source) {
  if (!source) {
    return null;
  }

  if (source.doc_id) {
    const byId = libraryTopics.find((topic) => topic.doc_id === source.doc_id);
    if (byId) {
      return byId;
    }
  }

  if (source.doc_title_match) {
    const marker = String(source.doc_title_match || "").toLowerCase();
    const byTitle = libraryTopics.find((topic) => String(topic.title || "").toLowerCase().includes(marker));
    if (byTitle) {
      return byTitle;
    }
  }

  return null;
}

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

function getStoredAuthToken() {
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || "";
}

function getStoredAuthRole() {
  return window.localStorage.getItem(AUTH_ROLE_STORAGE_KEY) || "user";
}

function setGlossaryAdminFeedback(message, kind = "neutral") {
  if (!glossaryAdminFeedback) {
    return;
  }
  glossaryAdminFeedback.textContent = message;
  glossaryAdminFeedback.classList.remove("is-error", "is-success", "empty-state");
  if (kind === "error") {
    glossaryAdminFeedback.classList.add("is-error");
  } else if (kind === "success") {
    glossaryAdminFeedback.classList.add("is-success");
  } else {
    glossaryAdminFeedback.classList.add("empty-state");
  }
}

function updateGlossaryAdminVisibility() {
  if (!glossaryAdminPanel) {
    return;
  }
  const isAdmin = getStoredAuthRole() === "admin" && Boolean(getStoredAuthToken());
  glossaryAdminPanel.classList.toggle("is-hidden", !isAdmin);
  if (glossaryAdminTabButton) {
    glossaryAdminTabButton.classList.toggle("is-hidden", !isAdmin);
  }
  if (!isAdmin && window.location.hash === "#glossary-admin") {
    setActiveTab("glossary");
  }
  if (isAdmin) {
    setGlossaryAdminFeedback("Режим редактирования активен. Вы можете создавать, изменять и удалять записи справочника.", "success");
  } else {
    setGlossaryAdminFeedback("Войдите под пользователем с ролью admin, чтобы редактировать справочник.", "neutral");
  }
}

function buildGlossarySourceRow(source = {}) {
  const row = document.createElement("div");
  row.className = "glossary-admin-source-row";
  row.innerHTML = `
    <div>
      <label class="auth-field-label">Название</label>
      <input class="auth-input" data-source-field="label" type="text" value="${escapeHtml(source.label || "")}" placeholder="Например: Ericsson EPC Mobility Management Guide" />
    </div>
    <div>
      <label class="auth-field-label">Поиск по заголовку</label>
      <input class="auth-input" data-source-field="doc_title_match" type="text" value="${escapeHtml(source.doc_title_match || "")}" placeholder="Подстрока заголовка документа" />
    </div>
    <div>
      <label class="auth-field-label">doc_id</label>
      <input class="auth-input" data-source-field="doc_id" type="text" value="${escapeHtml(source.doc_id || "")}" placeholder="Необязательно" />
    </div>
    <button type="button" class="auth-secondary glossary-admin-source-remove">Удалить</button>
  `;
  return row;
}

function renderGlossarySourceRows(sources = []) {
  if (!glossaryAdminSourcesList) {
    return;
  }
  glossaryAdminSourcesList.innerHTML = "";
  if (!sources.length) {
    glossaryAdminSourcesList.appendChild(buildGlossarySourceRow());
    return;
  }
  sources.forEach((source) => {
    glossaryAdminSourcesList.appendChild(buildGlossarySourceRow(source));
  });
}

function addGlossarySourceRow(source = {}) {
  if (!glossaryAdminSourcesList) {
    return;
  }
  glossaryAdminSourcesList.appendChild(buildGlossarySourceRow(source));
}

function setAuthSession(payload, fallbackDisplayName = "") {
  setAuthenticatedUser(payload.display_name || fallbackDisplayName || "Пользователь");
  if (payload.access_token) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, payload.access_token);
  }
  if (payload.role) {
    window.localStorage.setItem(AUTH_ROLE_STORAGE_KEY, payload.role);
  }
  updateGlossaryAdminVisibility();
}

function clearAuthSession() {
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(AUTH_ROLE_STORAGE_KEY);
  updateGlossaryAdminVisibility();
}

function buildAuthorizedHeaders(extraHeaders = {}) {
  const token = getStoredAuthToken();
  const headers = { ...extraHeaders };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function authorizedJson(url, options = {}) {
  const mergedOptions = { ...options };
  mergedOptions.headers = buildAuthorizedHeaders(options.headers || {});
  return fetchJson(url, mergedOptions);
}

function restoreAuthenticatedUser() {
  const savedName = window.localStorage.getItem(AUTH_USER_STORAGE_KEY);
  if (savedName) {
    setAuthenticatedUser(savedName);
  }
  updateGlossaryAdminVisibility();
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
  clearAuthSession();
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
  clearAuthSession();
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
    throw new Error(`Ошибка запроса: ${response.status}`);
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
    const detail = body.detail || `Ошибка запроса: ${response.status}`;
    throw new Error(detail);
  }
  return body;
}

async function loadDocument(docId) {
  setActiveTab("library");
  const documentData = await fetchJson(`/api/v1/documents/${docId}`);
  currentOpenedDocId = docId;
  docContent.classList.remove("empty-state");
  const parts = [
    `Название: ${documentData.title}`,
    `Продукт: ${documentData.metadata.product || "-"}`,
    `Вендор: ${documentData.metadata.vendor || "-"}`,
    `Домен: ${documentData.metadata.domain || "-"}`,
    `Релиз: ${documentData.metadata.release || "-"}`,
    "",
    ...documentData.chunks.map((chunk) => chunk.content),
  ];
  docContent.textContent = parts.join("\n");
}

function setAiHomeStatus(message, kind = "neutral") {
  if (!aiHomeStatus) {
    return;
  }
  aiHomeStatus.textContent = message;
  aiHomeStatus.classList.remove("is-error", "is-success", "empty-state");
  if (kind === "error") {
    aiHomeStatus.classList.add("is-error");
  } else if (kind === "success") {
    aiHomeStatus.classList.add("is-success");
  } else {
    aiHomeStatus.classList.add("empty-state");
  }
}

function renderAiHomeCitations(citations) {
  if (!aiHomeCitationsList) {
    return;
  }
  aiHomeCitationsList.innerHTML = "";

  if (!Array.isArray(citations) || citations.length === 0) {
    aiHomeCitationsList.innerHTML = '<li class="empty-state">Цитаты отсутствуют для этого ответа.</li>';
    return;
  }

  citations.forEach((citation, index) => {
    const item = document.createElement("li");
    const title = citation.title || citation.doc_id || `Источник ${index + 1}`;
    item.innerHTML = `<strong>${title}</strong><br /><small>Уверенность: ${citation.confidence || 0}</small>`;

    if (citation.doc_id) {
      const openButton = document.createElement("button");
      openButton.type = "button";
      openButton.className = "ai-citation-open";
      const isExternal = /^https?:\/\//i.test(citation.doc_id);
      openButton.textContent = isExternal ? "Открыть источник" : "Открыть документ";
      openButton.addEventListener("click", () => {
        if (isExternal) {
          window.open(citation.doc_id, "_blank", "noopener,noreferrer");
          return;
        }
        loadDocument(citation.doc_id).catch((error) => {
          setAiHomeStatus(error.message || "Не удалось открыть документ.", "error");
        });
      });
      item.appendChild(document.createElement("br"));
      item.appendChild(openButton);
    }

    aiHomeCitationsList.appendChild(item);
  });
}

function renderAiHomeAnswer(payload) {
  if (aiHomeAnswer) {
    aiHomeAnswer.classList.remove("empty-state");
    aiHomeAnswer.textContent = payload.answer || "Ответ не получен.";
  }
  renderAiHomeCitations(payload.citations || []);
}

async function submitAiHomeQuestion() {
  const question = (aiHomeQuestionInput?.value || "").trim();
  if (!question) {
    setAiHomeStatus("Введите вопрос для ИИ.", "error");
    return;
  }

  const mode = aiHomeModeInput?.value || "explain";
  const sourceScope = aiHomeSourceInput?.value || "local";
  const maxCitationsRaw = Number.parseInt(aiHomeMaxCitationsInput?.value || "3", 10);
  const maxCitations = Number.isNaN(maxCitationsRaw) ? 3 : Math.max(1, Math.min(10, maxCitationsRaw));
  const useCurrentDoc = Boolean(aiHomeUseCurrentDocInput?.checked);
  const contextDocIds = sourceScope === "local" && useCurrentDoc && currentOpenedDocId ? [currentOpenedDocId] : [];

  if (aiHomeSubmitButton) {
    aiHomeSubmitButton.disabled = true;
  }
  setAiHomeStatus("ИИ обрабатывает запрос...", "neutral");

  try {
    const payload = await postJson("/api/v1/ai/ask", {
      question,
      mode,
      max_citations: maxCitations,
      source_scope: sourceScope,
      context_doc_ids: contextDocIds,
    });
    renderAiHomeAnswer(payload);
    if (payload.blocked) {
      if (sourceScope === "internet") {
        setAiHomeStatus(`Ответ из интернета не подтвержден. Trace ID: ${payload.trace_id}. Проверьте интернет-соединение или выберите локальную библиотеку.`, "error");
      } else {
        setAiHomeStatus(`Ответ получен, но без подтвержденных цитат. Trace ID: ${payload.trace_id}. Уточните вопрос или откройте документ-контекст.`, "error");
      }
    } else {
      setAiHomeStatus(`Ответ получен. Trace ID: ${payload.trace_id}`, "success");
    }
  } catch (error) {
    setAiHomeStatus(error.message || "Не удалось получить ответ ИИ.", "error");
  } finally {
    if (aiHomeSubmitButton) {
      aiHomeSubmitButton.disabled = false;
    }
  }
}

function syncAiHomeSourceUi() {
  const isLocal = (aiHomeSourceInput?.value || "local") === "local";
  if (aiHomeUseCurrentDocInput) {
    aiHomeUseCurrentDocInput.disabled = !isLocal;
    if (!isLocal) {
      aiHomeUseCurrentDocInput.checked = false;
    }
  }
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

function flattenTopics(products) {
  return products.flatMap((product) =>
    product.releases.flatMap((release) =>
      release.domains.flatMap((domain) =>
        domain.topics.map((topic) => ({
          ...topic,
          product: product.name,
          release: topic.release || release.name,
          domain: domain.name,
        }))
      )
    )
  );
}

function getUniqueValues(topics, fieldName) {
  const values = topics
    .map((topic) => String(topic[fieldName] || "").trim())
    .filter(Boolean);
  return Array.from(new Set(values)).sort((left, right) => left.localeCompare(right, "ru"));
}

function toFilterFieldMap(topics) {
  return {
    node_type: getUniqueValues(topics, "node_type"),
    release: getUniqueValues(topics, "release"),
    product: getUniqueValues(topics, "product"),
  };
}

function reconcileActiveFilters(availableValues) {
  Object.entries(activeLibraryFilters).forEach(([fieldName, selectedValues]) => {
    const allowedValues = new Set(availableValues[fieldName] || []);
    Array.from(selectedValues).forEach((value) => {
      if (!allowedValues.has(value)) {
        selectedValues.delete(value);
      }
    });
  });
}

function buildFilterOptionsMarkup(fieldName, options) {
  if (!options.length) {
    return '<div class="filter-empty">Нет доступных значений</div>';
  }

  return options
    .map((value) => {
      const escapedValue = value.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      const checked = activeLibraryFilters[fieldName].has(value) ? " checked" : "";
      return `
        <label class="filter-option">
          <input type="checkbox" data-filter-field="${fieldName}" value="${escapedValue}"${checked} />
          <span>${escapedValue}</span>
        </label>
      `;
    })
    .join("");
}

function applyLibraryFilters(topics) {
  return topics.filter((topic) => {
    const byNodeType = activeLibraryFilters.node_type.size === 0 || activeLibraryFilters.node_type.has(String(topic.node_type || ""));
    const byRelease = activeLibraryFilters.release.size === 0 || activeLibraryFilters.release.has(String(topic.release || ""));
    const byProduct = activeLibraryFilters.product.size === 0 || activeLibraryFilters.product.has(String(topic.product || ""));
    return byNodeType && byRelease && byProduct;
  });
}

function getSearchFiltersPayload() {
  return {
    node_type: Array.from(activeLibraryFilters.node_type),
    release: Array.from(activeLibraryFilters.release),
    product: Array.from(activeLibraryFilters.product),
  };
}

function clearAllLibraryFilters() {
  Object.values(activeLibraryFilters).forEach((selectedValues) => selectedValues.clear());

  if (filtersContent) {
    filtersContent.querySelectorAll('input[type="checkbox"][data-filter-field]').forEach((input) => {
      if (input instanceof HTMLInputElement) {
        input.checked = false;
      }
    });
  }

  renderRecentTopics(applyLibraryFilters(libraryTopics));

  const query = searchInput?.value?.trim();
  if (query) {
    runSearch(query).catch((error) => {
      searchResults.classList.add("empty-state");
      searchResults.textContent = `Не удалось выполнить поиск: ${error.message}`;
    });
  }
}

function renderRecentTopics(topics) {
  recentList.innerHTML = "";
  const recentTopics = topics.slice(0, 8);
  if (!recentTopics.length) {
    recentList.innerHTML = '<li class="empty-state">По выбранным фильтрам библиотеки не найдены.</li>';
    return;
  }

  recentTopics.forEach((topic) => recentList.appendChild(buildRecentItem(topic)));
}

function getGlossaryEntriesFiltered(query) {
  if (!glossaryLoaded) {
    return [];
  }

  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) {
    return sortGlossaryEntries(glossaryEntries);
  }

  const filtered = glossaryEntries.filter((entry) => {
    const haystack = [entry.abbr, entry.termEn, entry.termRu, entry.definitionRu, entry.definitionEn].join(" ").toLowerCase();
    return haystack.includes(normalizedQuery);
  });
  return sortGlossaryEntries(filtered);
}

function formatManualSourcesForEditor(entry) {
  return (entry.manualSources || []).map((source) => ({
    label: source.label || "",
    doc_title_match: source.doc_title_match || "",
    doc_id: source.doc_id || "",
  }));
}

function fillGlossaryAdminForm(entry) {
  if (!glossaryAdminAbbrInput) {
    return;
  }
  const item = entry || {
    abbr: "",
    termRu: "",
    termEn: "",
    definitionRu: "",
    definitionEn: "",
    related: [],
    keywords: [],
    manualSources: [],
  };
  glossaryEditingOriginalAbbr = entry?.abbr || null;
  glossaryAdminAbbrInput.value = item.abbr || "";
  glossaryAdminTermRuInput.value = item.termRu || "";
  glossaryAdminTermEnInput.value = item.termEn || "";
  glossaryAdminDefinitionRuInput.value = item.definitionRu || "";
  glossaryAdminDefinitionEnInput.value = item.definitionEn || "";
  glossaryAdminRelatedInput.value = (item.related || []).join(", ");
  glossaryAdminKeywordsInput.value = (item.keywords || []).join(", ");
  renderGlossarySourceRows(formatManualSourcesForEditor(item));
}

function parseCommaSeparatedValues(rawValue) {
  return String(rawValue || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseManualSources() {
  if (!glossaryAdminSourcesList) {
    return [];
  }
  return Array.from(glossaryAdminSourcesList.querySelectorAll(".glossary-admin-source-row"))
    .map((row) => {
      const label = row.querySelector('[data-source-field="label"]')?.value?.trim() || "";
      const docTitleMatch = row.querySelector('[data-source-field="doc_title_match"]')?.value?.trim() || "";
      const docId = row.querySelector('[data-source-field="doc_id"]')?.value?.trim() || "";
      return {
        label,
        doc_title_match: docTitleMatch || null,
        doc_id: docId || null,
      };
    })
    .filter((item) => item.label);
}

function buildGlossaryAdminPayload() {
  return {
    abbr: (glossaryAdminAbbrInput?.value || "").trim(),
    term_ru: (glossaryAdminTermRuInput?.value || "").trim(),
    term_en: (glossaryAdminTermEnInput?.value || "").trim(),
    definition_ru: (glossaryAdminDefinitionRuInput?.value || "").trim(),
    definition_en: (glossaryAdminDefinitionEnInput?.value || "").trim(),
    related: parseCommaSeparatedValues(glossaryAdminRelatedInput?.value || ""),
    keywords: parseCommaSeparatedValues(glossaryAdminKeywordsInput?.value || ""),
    manual_sources: parseManualSources(),
  };
}

async function refreshGlossaryAfterWrite(nextAbbr = null) {
  await loadGlossaryEntries();
  if (nextAbbr) {
    activeGlossaryAbbr = nextAbbr;
  }
  renderGlossaryList(glossarySearchInput?.value || "");
  renderGlossaryAdminList();
  await loadGlossaryAuditLog();
}

function getFilteredAdminGlossaryEntries() {
  const query = normalizeSearchText(glossaryAdminFilter);
  if (!query) {
    return [...glossaryEntries].sort((left, right) => left.abbr.localeCompare(right.abbr, "en"));
  }
  return [...glossaryEntries]
    .filter((entry) => [entry.abbr, entry.termRu, entry.termEn, entry.definitionRu, entry.definitionEn].join(" ").toLowerCase().includes(query))
    .sort((left, right) => left.abbr.localeCompare(right.abbr, "en"));
}

function renderGlossaryAdminList() {
  if (!glossaryAdminList) {
    return;
  }
  if (!glossaryLoaded) {
    glossaryAdminList.innerHTML = '<li class="empty-state">Записи загружаются...</li>';
    return;
  }
  const entries = getFilteredAdminGlossaryEntries();
  const totalPages = Math.max(1, Math.ceil(entries.length / GLOSSARY_ADMIN_PAGE_SIZE));
  glossaryAdminPage = Math.min(Math.max(1, glossaryAdminPage), totalPages);
  const offset = (glossaryAdminPage - 1) * GLOSSARY_ADMIN_PAGE_SIZE;
  const pageItems = entries.slice(offset, offset + GLOSSARY_ADMIN_PAGE_SIZE);

  if (!pageItems.length) {
    glossaryAdminList.innerHTML = '<li class="empty-state">Подходящие записи не найдены.</li>';
  } else {
    glossaryAdminList.innerHTML = pageItems
      .map((entry) => `
        <li>
          <button type="button" class="glossary-item-button${entry.abbr === glossaryEditingOriginalAbbr ? " is-active" : ""}" data-glossary-admin-abbr="${escapeHtml(entry.abbr)}">
            <span class="glossary-item-abbr">${escapeHtml(entry.abbr)}</span>
            <span class="glossary-item-title">${escapeHtml(entry.termRu)}</span>
          </button>
        </li>
      `)
      .join("");
  }

  if (glossaryAdminPrevButton) {
    glossaryAdminPrevButton.disabled = glossaryAdminPage <= 1;
  }
  if (glossaryAdminNextButton) {
    glossaryAdminNextButton.disabled = glossaryAdminPage >= totalPages;
  }
  if (glossaryAdminPageStatus) {
    glossaryAdminPageStatus.textContent = `Страница ${glossaryAdminPage} из ${totalPages}`;
  }
}

async function exportGlossaryJson() {
  try {
    const payload = await authorizedJson("/api/v1/glossary/export");
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "glossary-export.json";
    anchor.click();
    URL.revokeObjectURL(url);
    setGlossaryAdminFeedback("Экспорт glossary.json выполнен.", "success");
  } catch (error) {
    setGlossaryAdminFeedback(error.message || "Не удалось экспортировать glossary.", "error");
  }
}

function downloadJsonFile(payload, fileName) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

function downloadGlossaryTemplate() {
  const payload = {
    entries: [
      {
        abbr: "AMF",
        term_ru: "Функция управления доступом и мобильностью",
        term_en: "Access and Mobility Management Function",
        definition_ru: "Описание на русском языке.",
        definition_en: "Description in English.",
        related: ["SMF", "AUSF"],
        keywords: ["amf", "mobility"],
        manual_sources: [
          {
            label: "Ericsson EPC Mobility Management Guide",
            doc_title_match: "Ericsson EPC Mobility Management Guide",
            doc_id: null,
          },
        ],
      },
    ],
  };
  downloadJsonFile(payload, "glossary-template.json");
  setGlossaryAdminFeedback("Шаблон glossary-template.json скачан.", "success");
}

async function loadGlossaryAuditLog() {
  if (!glossaryAdminAuditList) {
    return;
  }
  try {
    const payload = await authorizedJson("/api/v1/admin/audit?limit=200");
    const glossaryEvents = (Array.isArray(payload) ? payload : [])
      .filter((item) => String(item.action || "").startsWith("admin.glossary."))
      .slice(0, 30);

    if (!glossaryEvents.length) {
      glossaryAdminAuditList.innerHTML = '<li class="empty-state">События по справочнику пока отсутствуют.</li>';
      return;
    }

    glossaryAdminAuditList.innerHTML = glossaryEvents
      .map((event) => {
        const target = escapeHtml(event.target || "-");
        const actor = escapeHtml(event.actor_login || "-");
        const status = escapeHtml(event.status || "-");
        const action = escapeHtml(event.action || "-");
        const createdAt = escapeHtml(event.created_at || "-");
        return `<li><strong>${action}</strong> | target: ${target} | actor: ${actor} | status: ${status}<br /><small>${createdAt}</small></li>`;
      })
      .join("");
  } catch (error) {
    glossaryAdminAuditList.innerHTML = `<li class="empty-state">Не удалось загрузить журнал: ${escapeHtml(error.message || "unknown error")}</li>`;
  }
}

async function importGlossaryJson(file) {
  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const entries = Array.isArray(parsed) ? parsed : parsed.entries;
    if (!Array.isArray(entries)) {
      throw new Error("JSON должен содержать массив entries");
    }
    const payload = { entries, replace_existing: true };
    const response = await authorizedJson("/api/v1/glossary/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    activeGlossaryAbbr = null;
    fillGlossaryAdminForm(null);
    await loadGlossaryEntries();
    await loadGlossaryAuditLog();
    setGlossaryAdminFeedback(`Импорт завершен. Всего записей: ${response.imported}.`, "success");
  } catch (error) {
    setGlossaryAdminFeedback(error.message || "Не удалось импортировать glossary.", "error");
  }
}

function getGlossaryLinkedTopics(entry) {
  if (!Array.isArray(libraryTopics) || libraryTopics.length === 0) {
    return [];
  }

  const keywords = [entry.abbr, ...(entry.keywords || [])].map((item) => String(item || "").toLowerCase());
  const seen = new Set();
  const linked = [];

  libraryTopics.forEach((topic) => {
    if (!topic?.doc_id || seen.has(topic.doc_id)) {
      return;
    }

    const blob = [topic.title, topic.product, topic.release, topic.domain, topic.vendor].join(" ").toLowerCase();
    if (keywords.some((keyword) => keyword && blob.includes(keyword))) {
      seen.add(topic.doc_id);
      linked.push(topic);
    }
  });

  return linked.slice(0, 5);
}

function renderGlossaryDetails(entry) {
  if (!glossaryDetails) {
    return;
  }
  if (!entry) {
    glossaryDetails.classList.add("empty-state");
    glossaryDetails.textContent = "Выберите термин из списка слева, чтобы посмотреть описание и связанные документы.";
    return;
  }

  const relatedMarkup = (entry.related || [])
    .map((item) => `<span class="glossary-related-tag">${escapeHtml(item)}</span>`)
    .join("");

  const pinnedResolved = (entry.manualSources || []).map((source) => ({
    source,
    topic: resolveGlossaryManualSource(source),
  }));

  const pinnedMarkup = pinnedResolved.length
    ? pinnedResolved
      .map(({ source, topic }) => {
        if (!topic) {
          const label = escapeHtml(source.label || source.doc_title_match || source.doc_id || "Источник");
          return `
            <button type="button" class="glossary-doc-link is-missing" disabled>
              ${label}
              <small>Источник пока недоступен в загруженных документах</small>
            </button>
          `;
        }

        return `
          <button type="button" class="glossary-doc-link" data-doc-id="${topic.doc_id}">
            ${escapeHtml(source.label || topic.title)}
            <small>${escapeHtml(topic.product || "-")} | ${escapeHtml(topic.release || "-")}</small>
          </button>
        `;
      })
      .join("")
    : '<p class="glossary-pinned-empty">Закрепленные источники пока не настроены.</p>';

  const linkedTopics = getGlossaryLinkedTopics(entry);
  const pinnedDocIds = new Set(
    pinnedResolved.filter((item) => item.topic?.doc_id).map((item) => item.topic.doc_id)
  );

  const linkedTopicsFiltered = linkedTopics.filter((topic) => !pinnedDocIds.has(topic.doc_id));
  const docLinksMarkup = linkedTopicsFiltered.length
    ? linkedTopicsFiltered
      .map(
        (topic) => `
          <button type="button" class="glossary-doc-link" data-doc-id="${topic.doc_id}">
            ${escapeHtml(topic.title)}
            <small>${escapeHtml(topic.product || "-")} | ${escapeHtml(topic.release || "-")}</small>
          </button>
        `
      )
      .join("")
    : '<p class="empty-state">Для этого термина пока не найдено прямых совпадений в загруженных документах.</p>';

  glossaryDetails.classList.remove("empty-state");
  glossaryDetails.innerHTML = `
    <h3>${escapeHtml(entry.abbr)}</h3>
    <p class="glossary-meta"><strong>${escapeHtml(getGlossaryTerm(entry))}</strong><br />${escapeHtml(getGlossarySecondaryTerm(entry))}</p>
    <p>${escapeHtml(getGlossaryDefinition(entry))}</p>

    <h4 class="glossary-block-title">Закрепленные источники</h4>
    <div class="glossary-pinned-links">${pinnedMarkup}</div>

    <h4 class="glossary-block-title">Связанные термины</h4>
    <div class="glossary-related">${relatedMarkup || '<span class="empty-state">Нет связанных терминов</span>'}</div>

    <h4 class="glossary-block-title">Связанные документы</h4>
    <div class="glossary-doc-links">${docLinksMarkup}</div>
  `;

  fillGlossaryAdminForm(entry);
}

async function saveGlossaryEntry() {
  const token = getStoredAuthToken();
  if (!token || getStoredAuthRole() !== "admin") {
    setGlossaryAdminFeedback("Требуется вход под пользователем с ролью admin.", "error");
    return;
  }

  const payload = buildGlossaryAdminPayload();
  if (!payload.abbr || !payload.term_ru || !payload.term_en || !payload.definition_ru || !payload.definition_en) {
    setGlossaryAdminFeedback("Заполните аббревиатуру, названия и оба описания.", "error");
    return;
  }

  try {
    const method = glossaryEditingOriginalAbbr ? "PATCH" : "POST";
    const url = glossaryEditingOriginalAbbr ? `/api/v1/glossary/${encodeURIComponent(glossaryEditingOriginalAbbr)}` : "/api/v1/glossary";
    const response = await authorizedJson(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    activeGlossaryAbbr = response.abbr;
    await refreshGlossaryAfterWrite(response.abbr);
    setGlossaryAdminFeedback(`Запись ${response.abbr} сохранена.`, "success");
  } catch (error) {
    setGlossaryAdminFeedback(error.message || "Не удалось сохранить запись.", "error");
  }
}

async function deleteGlossaryEntryFromAdmin() {
  const token = getStoredAuthToken();
  if (!token || getStoredAuthRole() !== "admin") {
    setGlossaryAdminFeedback("Требуется вход под пользователем с ролью admin.", "error");
    return;
  }
  if (!glossaryEditingOriginalAbbr) {
    setGlossaryAdminFeedback("Сначала выберите существующую запись для удаления.", "error");
    return;
  }
  const targetAbbr = glossaryEditingOriginalAbbr;
  try {
    await authorizedJson(`/api/v1/glossary/${encodeURIComponent(targetAbbr)}`, {
      method: "DELETE",
    });
    activeGlossaryAbbr = null;
    fillGlossaryAdminForm(null);
    await refreshGlossaryAfterWrite();
    setGlossaryAdminFeedback(`Запись ${targetAbbr} удалена.`, "success");
  } catch (error) {
    setGlossaryAdminFeedback(error.message || "Не удалось удалить запись.", "error");
  }
}

function startNewGlossaryEntry() {
  activeGlossaryAbbr = null;
  fillGlossaryAdminForm(null);
  setGlossaryAdminFeedback("Подготовлена новая запись. Заполните форму и нажмите «Сохранить».", "neutral");
}

function renderGlossaryList(query = "") {
  if (!glossaryList) {
    return;
  }

  if (!glossaryLoaded) {
    glossaryList.innerHTML = '<li class="empty-state">Термины загружаются...</li>';
    return;
  }

  const entries = getGlossaryEntriesFiltered(query);
  if (!entries.length) {
    glossaryList.innerHTML = '<li class="empty-state">По вашему запросу термины не найдены.</li>';
    renderGlossaryDetails(null);
    return;
  }

  if (!activeGlossaryAbbr || !entries.some((entry) => entry.abbr === activeGlossaryAbbr)) {
    activeGlossaryAbbr = entries[0].abbr;
  }

  glossaryList.innerHTML = entries
    .map(
      (entry) => `
        <li>
          <button type="button" class="glossary-item-button${entry.abbr === activeGlossaryAbbr ? " is-active" : ""}" data-glossary-abbr="${entry.abbr}">
            <span class="glossary-item-abbr">${escapeHtml(entry.abbr)}</span>
            <span class="glossary-item-title">${escapeHtml(getGlossaryTerm(entry))}</span>
          </button>
        </li>
      `
    )
    .join("");

  const activeEntry = glossaryEntries.find((entry) => entry.abbr === activeGlossaryAbbr) || entries[0];
  renderGlossaryDetails(activeEntry);
}

function hideSearchSuggestions() {
  if (!searchSuggestions) {
    return;
  }
  searchSuggestions.innerHTML = "";
  searchSuggestions.classList.add("is-hidden");
}

function normalizeSearchText(value) {
  return String(value || "").trim().toLowerCase();
}

function getSearchSuggestions(query) {
  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) {
    return [];
  }

  const uniqueByDocId = new Map();
  libraryTopics.forEach((topic) => {
    if (!topic?.doc_id) {
      return;
    }
    if (!uniqueByDocId.has(topic.doc_id)) {
      uniqueByDocId.set(topic.doc_id, topic);
    }
  });

  return Array.from(uniqueByDocId.values())
    .filter((topic) => {
      const title = normalizeSearchText(topic.title);
      return title.includes(normalizedQuery);
    })
    .sort((left, right) => left.title.localeCompare(right.title, "ru"))
    .slice(0, 8);
}

function renderSearchSuggestions(query) {
  if (!searchSuggestions) {
    return;
  }

  const suggestions = getSearchSuggestions(query);
  if (!suggestions.length) {
    hideSearchSuggestions();
    return;
  }

  searchSuggestions.innerHTML = suggestions
    .map((topic) => {
      const title = String(topic.title || "");
      const product = String(topic.product || "-");
      const release = String(topic.release || "-");
      const escapedTitle = title.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      const escapedProduct = product.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      const escapedRelease = release.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      return `
        <li>
          <button type="button" class="search-suggestions-item" data-doc-id="${topic.doc_id}">
            ${escapedTitle}
            <span class="search-suggestions-meta">${escapedProduct} | ${escapedRelease}</span>
          </button>
        </li>
      `;
    })
    .join("");

  searchSuggestions.classList.remove("is-hidden");
}

function buildResultButton(hit) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Открыть документ";
  button.addEventListener("click", () => loadDocument(hit.doc_id));
  return button;
}

function renderFilters(topics) {
  const availableValues = toFilterFieldMap(topics);
  reconcileActiveFilters(availableValues);

  LIBRARY_FILTER_CONFIG.forEach(({ field, detailIndex }) => {
    const details = filtersContent.querySelector(`details:nth-of-type(${detailIndex})`);
    if (!details) {
      return;
    }

    const summaryCount = details.querySelector("summary span");
    if (summaryCount) {
      summaryCount.textContent = `(${availableValues[field].length})`;
    }

    details.querySelectorAll(".filter-option, .filter-empty").forEach((node) => node.remove());
    details.insertAdjacentHTML("beforeend", buildFilterOptionsMarkup(field, availableValues[field]));
  });
}

function renderTree(products) {
  libraryTopics = flattenTopics(products);
  renderFilters(libraryTopics);
  renderGlossaryList(glossarySearchInput?.value || "");

  if (!libraryTopics.length) {
    recentList.innerHTML = '<li class="empty-state">Библиотеки пока не загружены.</li>';
    return;
  }

  renderRecentTopics(applyLibraryFilters(libraryTopics));
}

async function loadTree() {
  try {
    const treeData = await fetchJson("/api/v1/documents/tree");
    renderTree(treeData.products);
  } catch (error) {
    recentList.innerHTML = `<li class="empty-state">Не удалось загрузить библиотеку: ${error.message}</li>`;
  }
}

async function runSearch(query) {
  lastSearchQuery = query;
  const payload = await fetchJson("/api/v1/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      page: 1,
      size: 10,
      filters: getSearchFiltersPayload(),
    }),
  });
  renderSearchResults(payload);
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

  await runSearch(query);
  hideSearchSuggestions();
}

async function handleRefreshSearchResults() {
  setActiveTab("library");
  const query = searchInput?.value?.trim() || lastSearchQuery;
  if (!query) {
    searchResults.classList.add("empty-state");
    searchResults.textContent = "Введите запрос, чтобы обновить результаты поиска.";
    return;
  }

  try {
    await runSearch(query);
    hideSearchSuggestions();
  } catch (error) {
    searchResults.classList.add("empty-state");
    searchResults.textContent = `Не удалось обновить результаты поиска: ${error.message}`;
  }
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
  const phone = mode === "phone" ? normalizeRuPhoneForApi(registerPhone?.value || "") : null;
  const email = mode === "email" ? (registerEmail?.value || "").trim() : null;
  return { login, password, phone, email };
}

function normalizeRuPhoneDigits(rawPhone) {
  const digits = String(rawPhone || "").replace(/\D/g, "");
  if (!digits) {
    return "";
  }
  if (digits[0] === "8") {
    return (`7${digits.slice(1)}`).slice(0, 11);
  }
  if (digits[0] === "7") {
    return digits.slice(0, 11);
  }
  return (`7${digits}`).slice(0, 11);
}

function formatRuPhoneInput(rawPhone) {
  const digits = normalizeRuPhoneDigits(rawPhone);
  if (!digits) {
    return "+7";
  }

  const national = digits.slice(1);
  const parts = [];
  if (national.length > 0) {
    parts.push(`(${national.slice(0, 3)}`);
  }
  if (national.length >= 3) {
    parts[0] += ")";
  }
  if (national.length > 3) {
    parts.push(national.slice(3, 6));
  }
  if (national.length > 6) {
    parts.push(national.slice(6, 8));
  }
  if (national.length > 8) {
    parts.push(national.slice(8, 10));
  }

  return parts.length ? `+7 ${parts.join(" ")}` : "+7";
}

function countDigitsBeforeIndex(rawValue, index) {
  return String(rawValue || "")
    .slice(0, Math.max(0, index))
    .replace(/\D/g, "").length;
}

function findCaretByDigitCount(formattedValue, digitCount) {
  const normalizedCount = Math.max(0, digitCount);
  if (normalizedCount === 0) {
    return 0;
  }

  let seenDigits = 0;
  for (let index = 0; index < formattedValue.length; index += 1) {
    if (/\d/.test(formattedValue[index])) {
      seenDigits += 1;
      if (seenDigits >= normalizedCount) {
        return index + 1;
      }
    }
  }
  return formattedValue.length;
}

function normalizeRuPhoneForApi(rawPhone) {
  const digits = normalizeRuPhoneDigits(rawPhone);
  if (!digits) {
    return "";
  }
  return `+${digits}`;
}

function isCompleteRuPhone(rawPhone) {
  return normalizeRuPhoneDigits(rawPhone).length === 11;
}

function bindRuPhoneInput(inputElement) {
  if (!inputElement) {
    return;
  }
  inputElement.addEventListener("focus", () => {
    if (!inputElement.value.trim()) {
      inputElement.value = "+7";
      return;
    }
    inputElement.value = formatRuPhoneInput(inputElement.value);
  });
  inputElement.addEventListener("input", () => {
    const rawValue = inputElement.value;
    const rawCaret = inputElement.selectionStart ?? rawValue.length;
    const digitsBeforeCaret = countDigitsBeforeIndex(rawValue, rawCaret);
    const formatted = formatRuPhoneInput(rawValue);
    const targetDigit = digitsBeforeCaret === 0 ? 1 : digitsBeforeCaret;

    inputElement.value = formatted;

    const nextCaret = findCaretByDigitCount(formatted, targetDigit);
    if (typeof inputElement.setSelectionRange === "function") {
      inputElement.setSelectionRange(nextCaret, nextCaret);
    }
  });
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
    setAuthSession(payload, payload.display_name || getRegistrationPayload().login);
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

function clearSmsAuthFields() {
  if (phoneInput) {
    phoneInput.value = "";
  }
  if (smsCodeInput) {
    smsCodeInput.value = "";
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
      setAuthFeedback("QR-сессия истекла. Обновите QR-код.", "error");
      stopQrPolling();
      return;
    }
    setAuthFeedback("Ожидаем сканирование QR-кода...", "neutral");
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
    setAuthFeedback("QR-код создан. Отсканируйте его в мобильном приложении.", "neutral");
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
    setAuthSession(payload, login);
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
  const rawPhone = phoneInput?.value || "";
  if (!isCompleteRuPhone(rawPhone)) {
    setAuthFeedback("Введите номер телефона в формате +7XXXXXXXXXX.", "error");
    return;
  }
  try {
    const phone = normalizeRuPhoneForApi(rawPhone);
    const payload = await postJson("/api/v1/auth/sms/send-code", { phone });
    const demoCode = payload.demo_code ? ` Демо-код: ${payload.demo_code}.` : "";
    setAuthFeedback(`Код отправлен на ${payload.phone_masked}.${demoCode}`, "success");
  } catch (error) {
    setAuthFeedback(error.message, "error");
  }
}

async function verifySmsCode() {
  const rawPhone = phoneInput?.value || "";
  const phone = normalizeRuPhoneForApi(rawPhone);
  const code = (smsCodeInput?.value || "").trim();
  if (!isCompleteRuPhone(rawPhone) || !code) {
    setAuthFeedback("Введите номер телефона и код из СМС.", "error");
    return;
  }
  try {
    const payload = await postJson("/api/v1/auth/sms/verify", { phone, code });
    setAuthSession(payload, payload.display_name || "Пользователь");
    setAuthFeedback("Код подтвержден. Вход выполнен успешно.", "success");
    clearSmsAuthFields();
    closeAuthMenu();
    closeAuthModal();
  } catch (error) {
    setAuthFeedback(error.message, "error");
  }
}

async function confirmQrScan() {
  if (!currentQrSessionId) {
    setAuthFeedback("Сначала обновите QR-код.", "error");
    return;
  }
  try {
    const payload = await postJson("/api/v1/auth/qr/confirm", { session_id: currentQrSessionId });
    setAuthSession(payload, payload.display_name || "Пользователь");
    setAuthFeedback("Вход по QR подтвержден. Авторизация успешна.", "success");
    stopQrPolling();
    closeAuthMenu();
    closeAuthModal();
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

bindRuPhoneInput(phoneInput);
bindRuPhoneInput(registerPhone);

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

if (aiHomeSubmitButton) {
  aiHomeSubmitButton.addEventListener("click", submitAiHomeQuestion);
}

if (aiHomeQuestionInput) {
  aiHomeQuestionInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      submitAiHomeQuestion();
    }
  });
}

if (aiHomeSourceInput) {
  aiHomeSourceInput.addEventListener("change", syncAiHomeSourceUi);
  syncAiHomeSourceUi();
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

document.addEventListener("click", (event) => {
  if (!searchSuggestions || !searchInput) {
    return;
  }
  if (event.target === searchInput || searchInput.contains(event.target) || searchSuggestions.contains(event.target)) {
    return;
  }
  hideSearchSuggestions();
});

window.addEventListener("hashchange", () => {
  const tabFromHash = normalizeHashTab(window.location.hash);
  setActiveTab(tabFromHash, { updateHash: false });
});

if (filtersContent) {
  filtersContent.addEventListener("change", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLInputElement) || target.type !== "checkbox") {
      return;
    }

    const fieldName = target.dataset.filterField;
    if (!fieldName || !activeLibraryFilters[fieldName]) {
      return;
    }

    if (target.checked) {
      activeLibraryFilters[fieldName].add(target.value);
    } else {
      activeLibraryFilters[fieldName].delete(target.value);
    }

    renderRecentTopics(applyLibraryFilters(libraryTopics));

    const query = searchInput?.value?.trim();
    if (query) {
      runSearch(query).catch((error) => {
        searchResults.classList.add("empty-state");
        searchResults.textContent = `Не удалось выполнить поиск: ${error.message}`;
      });
    }
  });
}

if (filtersResetButton) {
  filtersResetButton.addEventListener("click", clearAllLibraryFilters);
}

if (searchInput) {
  searchInput.addEventListener("input", (event) => {
    renderSearchSuggestions(event.target.value || "");
  });

  searchInput.addEventListener("focus", () => {
    if (searchInput.value.trim()) {
      renderSearchSuggestions(searchInput.value);
    }
  });

  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      hideSearchSuggestions();
    }
  });
}

if (searchSuggestions) {
  searchSuggestions.addEventListener("click", (event) => {
    const button = event.target.closest(".search-suggestions-item");
    if (!button || !searchInput) {
      return;
    }

    const docId = button.dataset.docId;
    const title = button.firstChild?.textContent?.trim() || "";
    searchInput.value = title;
    hideSearchSuggestions();

    if (docId) {
      loadDocument(docId).catch((error) => {
        searchResults.classList.add("empty-state");
        searchResults.textContent = `Не удалось открыть документ: ${error.message}`;
      });
    }
  });
}

if (glossarySearchInput) {
  glossarySearchInput.addEventListener("input", (event) => {
    renderGlossaryList(event.target.value || "");
  });
}

if (glossaryLanguageSelect) {
  glossaryLanguageSelect.addEventListener("change", (event) => {
    glossaryLanguage = event.target.value || "ru";
    renderGlossaryList(glossarySearchInput?.value || "");
  });
}

if (glossarySortSelect) {
  glossarySortSelect.addEventListener("change", (event) => {
    glossarySortMode = event.target.value || "abbr";
    renderGlossaryList(glossarySearchInput?.value || "");
  });
}

if (glossaryList) {
  glossaryList.addEventListener("click", (event) => {
    const button = event.target.closest(".glossary-item-button");
    if (!button) {
      return;
    }

    const abbr = button.dataset.glossaryAbbr;
    if (!abbr) {
      return;
    }

    activeGlossaryAbbr = abbr;
    renderGlossaryList(glossarySearchInput?.value || "");
  });
}

if (glossaryAdminSearchInput) {
  glossaryAdminSearchInput.addEventListener("input", (event) => {
    glossaryAdminFilter = event.target.value || "";
    glossaryAdminPage = 1;
    renderGlossaryAdminList();
  });
}

if (glossaryAdminList) {
  glossaryAdminList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-glossary-admin-abbr]");
    if (!button) {
      return;
    }
    const abbr = button.dataset.glossaryAdminAbbr;
    const entry = glossaryEntries.find((item) => item.abbr === abbr);
    if (!entry) {
      return;
    }
    glossaryEditingOriginalAbbr = entry.abbr;
    fillGlossaryAdminForm(entry);
    renderGlossaryAdminList();
  });
}

if (glossaryAdminPrevButton) {
  glossaryAdminPrevButton.addEventListener("click", () => {
    glossaryAdminPage = Math.max(1, glossaryAdminPage - 1);
    renderGlossaryAdminList();
  });
}

if (glossaryAdminNextButton) {
  glossaryAdminNextButton.addEventListener("click", () => {
    glossaryAdminPage += 1;
    renderGlossaryAdminList();
  });
}

if (glossaryAdminImportButton && glossaryAdminImportFileInput) {
  glossaryAdminImportButton.addEventListener("click", () => glossaryAdminImportFileInput.click());
  glossaryAdminImportFileInput.addEventListener("change", async () => {
    const file = glossaryAdminImportFileInput.files?.[0];
    if (!file) {
      return;
    }
    await importGlossaryJson(file);
    glossaryAdminImportFileInput.value = "";
  });
}

if (glossaryAdminTemplateButton) {
  glossaryAdminTemplateButton.addEventListener("click", downloadGlossaryTemplate);
}

if (glossaryAdminExportButton) {
  glossaryAdminExportButton.addEventListener("click", exportGlossaryJson);
}

if (glossaryAdminAuditRefreshButton) {
  glossaryAdminAuditRefreshButton.addEventListener("click", loadGlossaryAuditLog);
}

if (glossaryAdminNewButton) {
  glossaryAdminNewButton.addEventListener("click", startNewGlossaryEntry);
}

if (glossaryAdminSaveButton) {
  glossaryAdminSaveButton.addEventListener("click", saveGlossaryEntry);
}

if (glossaryAdminDeleteButton) {
  glossaryAdminDeleteButton.addEventListener("click", deleteGlossaryEntryFromAdmin);
}

if (glossaryAdminAddSourceButton) {
  glossaryAdminAddSourceButton.addEventListener("click", () => addGlossarySourceRow());
}

if (glossaryAdminSourcesList) {
  glossaryAdminSourcesList.addEventListener("click", (event) => {
    const removeButton = event.target.closest(".glossary-admin-source-remove");
    if (!removeButton) {
      return;
    }
    const row = removeButton.closest(".glossary-admin-source-row");
    row?.remove();
    if (!glossaryAdminSourcesList.children.length) {
      addGlossarySourceRow();
    }
  });
}

if (glossaryDetails) {
  glossaryDetails.addEventListener("click", (event) => {
    const button = event.target.closest(".glossary-doc-link");
    if (!button) {
      return;
    }

    const docId = button.dataset.docId;
    if (!docId) {
      return;
    }

    loadDocument(docId).catch((error) => {
      renderGlossaryDetails({
        abbr: "Ошибка",
        termEn: "Document open error",
        termRu: "Не удалось открыть документ",
        definitionRu: error.message || "Ошибка загрузки документа.",
        definitionEn: error.message || "Document loading error.",
        related: [],
        keywords: [],
        manualSources: [],
      });
    });
  });
}

searchForm.addEventListener("submit", handleSearch);
refreshTreeButton.addEventListener("click", handleRefreshSearchResults);

setActiveTab(normalizeHashTab(window.location.hash), { updateHash: false });

if (!window.location.hash || !tabViews[normalizeHashTab(window.location.hash)]) {
  window.location.hash = `#${DEFAULT_TAB}`;
}

restoreAuthenticatedUser();
updateRegisterContactFields();
renderGlossaryList();
loadGlossaryEntries();
loadGlossaryAuditLog();
loadTree();