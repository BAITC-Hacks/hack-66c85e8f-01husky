"use strict";
const $ = (id) => document.getElementById(id);
let tables = [], selected = "meetings", offset = 0, total = 0, sequence = 0;
let query = "", meeting = "", busy = false;
const size = 50;
const display = (value) => value === null ? "NULL" : typeof value === "object" ? JSON.stringify(value, null, 2) : String(value);
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function signOutView() {
  sequence++;
  tables = [];
  $("detail").close();
  for (const id of ["records", "columns", "tables", "stats", "detail-fields"]) $(id).replaceChildren();
  $("workspace").hidden = true;
  $("login").hidden = false;
}
async function api(path, options = {}) {
  const response = await fetch(`/api/v1${path}`, { ...options, credentials: "same-origin", cache: "no-store" });
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) signOutView();
    throw new Error(response.status === 401 ? "Войдите в аккаунт. Проверьте email и пароль." : response.status === 403 ? "Доступ разрешён только администратору." : `Не удалось загрузить данные (HTTP ${response.status}).`);
  }
  return response.status === 204 ? null : response.json();
}
function pagination() {
  $("previous").disabled = busy || offset === 0;
  $("next").disabled = busy || offset + size >= total;
}
function sidebar() {
  $("tables").replaceChildren(...tables.map((table) => {
    const button = node("button", undefined, table.name === selected ? "active" : "");
    button.type = "button";
    button.setAttribute("aria-pressed", String(table.name === selected));
    button.append(node("span", table.label), node("span", table.count.toLocaleString("ru-RU"), "count"));
    button.onclick = () => {
      selected = table.name; offset = 0; query = ""; meeting = "";
      $("search").value = ""; $("meeting-id").value = "";
      sidebar(); loadRows();
    };
    return button;
  }));
  $("stats").replaceChildren(...["meetings", "segments", "tasks", "participants"].map((name) => {
    const table = tables.find((item) => item.name === name);
    const card = node("div", undefined, "stat");
    card.append(node("span", table.label), node("strong", table.count.toLocaleString("ru-RU")));
    return card;
  }));
}
function openRecord(row) {
  $("detail-title").textContent = `${tables.find((table) => table.name === selected).label} · ${row.id ?? "запись"}`;
  $("detail-fields").replaceChildren(...Object.entries(row).flatMap(([key, value]) => [node("dt", key), node("dd", display(value))]));
  $("detail").showModal();
}
async function loadRows() {
  const request = ++sequence;
  const table = tables.find((item) => item.name === selected);
  if (!table) return;
  busy = true; pagination();
  $("error").hidden = true; $("empty").hidden = true;
  $("records").replaceChildren();
  $("title").textContent = table.label;
  $("subtitle").textContent = `public.${table.name} · ${table.columns.length} открытых полей`;
  $("meeting-filter").hidden = !table.meeting_filter;
  $("page-info").textContent = "Загружаем записи…";
  const head = node("tr");
  head.append(node("th", "Запись"), ...table.columns.map((column) => {
    const th = node("th", column.name); th.title = `${column.type}${column.nullable ? " · nullable" : ""}`; return th;
  }));
  $("columns").replaceChildren(head);
  const params = new URLSearchParams({ offset, limit: size, q: query });
  if (meeting && table.meeting_filter) params.set("meeting_id", meeting);
  try {
    const data = await api(`/admin/tables/${selected}?${params}`);
    if (request !== sequence) return;
    total = data.total;
    if (!data.rows.length && offset > 0 && total <= offset) {
      offset = Math.max(0, Math.floor((total - 1) / size) * size); return loadRows();
    }
    $("records").replaceChildren(...data.rows.map((row) => {
      const tr = node("tr"), action = node("td"), button = node("button", "Открыть ↗");
      button.type = "button"; button.onclick = () => openRecord(row); action.append(button); tr.append(action);
      for (const column of table.columns) {
        const value = row[column.name], td = node("td");
        td.append(node("span", display(value), value === null ? "value null" : "value")); tr.append(td);
      }
      return tr;
    }));
    $("empty").hidden = data.rows.length !== 0;
    $("empty").textContent = query || meeting ? "Ничего не найдено. Измените поиск или ID встречи." : "В этой таблице пока нет записей.";
    $("page-info").textContent = total ? `${offset + 1}–${offset + data.rows.length} из ${total.toLocaleString("ru-RU")} записей` : "0 записей";
  } catch (error) {
    if (request !== sequence) return;
    $("error").textContent = error.message; $("error").hidden = false;
    $("page-info").textContent = "Данные не загружены"; total = 0;
  } finally {
    if (request === sequence) { busy = false; pagination(); }
  }
}
async function enter() {
  const user = await api("/auth/me");
  const result = await api("/admin/tables");
  tables = result.tables;
  $("account").textContent = user.email;
  $("login").hidden = true; $("workspace").hidden = false;
  $("login-error").textContent = ""; $("password").value = "";
  sidebar(); await loadRows();
}
$("login-form").onsubmit = async (event) => {
  event.preventDefault(); $("login-button").disabled = true; $("login-error").textContent = "";
  try {
    await api("/auth/login", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({email: $("email").value, password: $("password").value})});
    await enter();
  } catch (error) { $("login-error").textContent = error.message; }
  finally { $("login-button").disabled = false; }
};
$("logout").onclick = async () => {
  try { await api("/auth/logout", { method: "POST" }); signOutView(); }
  catch (error) { $("error").textContent = error.message; $("error").hidden = false; }
};
$("filters").onsubmit = (event) => {event.preventDefault(); offset = 0; query = $("search").value; meeting = $("meeting-id").value; loadRows();};
$("refresh").onclick = async () => {
  try { const result = await api("/admin/tables"); tables = result.tables; sidebar(); await loadRows(); }
  catch (error) { $("error").textContent = error.message; $("error").hidden = false; }
};
$("previous").onclick = () => { offset = Math.max(0, offset - size); loadRows(); };
$("next").onclick = () => { offset += size; loadRows(); };
$("close-detail").onclick = () => $("detail").close();
enter().catch((error) => { if (!error.message.startsWith("Войдите")) $("login-error").textContent = error.message; });
