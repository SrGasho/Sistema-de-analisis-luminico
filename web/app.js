const state = { config: null, result: null, current: null };
const $ = (selector) => document.querySelector(selector);

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "No se pudo completar la solicitud");
  return payload;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function card(label, value) {
  return `<div class="card"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function input(path, value, type = "number", step = "0.1") {
  return `<input data-path="${path}" type="${type}" value="${escapeHtml(value)}" ${type === "number" ? `step="${step}"` : ""}>`;
}

function renderScenario(payload) {
  state.config = payload.config;
  state.current = payload.analisis_actual;
  const climateOptions = Object.keys(state.config.perfiles_climaticos).map((name) => `<option value="${name}" ${name === state.config.hotel.perfil_climatico ? "selected" : ""}>${name}</option>`).join("");
  $("#climate-select").innerHTML = climateOptions;
  $("#generator-capacity").value = state.config.generador.capacidad_kw;
  renderTowerForms();
  renderActivityForms();
  renderScheduleForms();
  renderMaterialForms();
  bindInputs();
  $("#validation-status").textContent = "Escenario cargado";
  renderCurrentAnalysis(state.current);
  $("#main-balance-button").disabled = false;
}

function renderTowerForms() {
  $("#tower-forms").innerHTML = state.config.torres.map((tower, index) => `<div class="tower-form"><strong>${escapeHtml(tower.id)}</strong><div class="mini-grid"><label>Pisos${input(`torres.${index}.pisos`, tower.pisos, "number", "1")}</label><label>Habitaciones/piso${input(`torres.${index}.habitaciones_por_piso`, tower.habitaciones_por_piso, "number", "1")}</label><label>Habitaciones ocupadas${input(`torres.${index}.habitaciones_ocupadas`, tower.habitaciones_ocupadas, "number", "1")}</label></div></div>`).join("");
}

function renderActivityForms() {
  const names = Object.keys(state.config.perfiles_iluminacion);
  $("#activity-forms").innerHTML = `<div class="activity-grid">${names.map((name) => {
    const profile = state.config.perfiles_iluminacion[name];
    const light = state.config.luminarias[name];
    return `<div class="activity-card"><h4>${name}</h4><div class="mini-grid"><label>Mínimo${input(`perfiles_iluminacion.${name}.minimo`, profile.minimo)}</label><label>Objetivo${input(`perfiles_iluminacion.${name}.objetivo`, profile.objetivo)}</label><label>Máximo${input(`perfiles_iluminacion.${name}.maximo`, profile.maximo)}</label><label>Potencia W${input(`luminarias.${name}.potencia_w`, light.potencia_w)}</label></div></div>`;
  }).join("")}</div>`;
}

function renderScheduleForms() {
  $("#schedule-forms").innerHTML = Object.entries(state.config.horarios).map(([name, schedule]) => `<div class="schedule-row"><strong>${name}</strong>${input(`horarios.${name}.inicio_activa`, schedule.inicio_activa, "number", "1")}${input(`horarios.${name}.fin_activa`, schedule.fin_activa, "number", "1")}</div>`).join("");
}

function renderMaterialForms() {
  const glass = Object.entries(state.config.vidrios).map(([name, value]) => `<div class="material-row"><strong>${name}</strong>${input(`vidrios.${name}.transmitancia_visible`, value.transmitancia_visible)}</div>`).join("");
  const walls = Object.entries(state.config.paredes).map(([name, value]) => `<div class="material-row"><strong>${name}</strong>${input(`paredes.${name}.reflectancia`, value.reflectancia)}</div>`).join("");
  $("#material-forms").innerHTML = `<p class="muted">Transmitancia visible</p>${glass}<p class="muted">Reflectancia</p>${walls}`;
}

function setPath(path, rawValue) {
  const parts = path.split(".");
  let target = state.config;
  parts.slice(0, -1).forEach((part) => { target = target[Number.isInteger(Number(part)) && part !== "" ? Number(part) : part]; });
  const last = parts[parts.length - 1];
  target[Number.isInteger(Number(last)) && last !== "" ? Number(last) : last] = rawValue;
}

function bindInputs() {
  document.querySelectorAll("[data-path]").forEach((element) => {
    element.addEventListener("input", () => {
      setPath(element.dataset.path, element.type === "number" ? Number(element.value) : element.value);
      $("#validation-status").textContent = "Cambios pendientes de analizar";
      $("#current-status").textContent = "La condición actual corresponde a la configuración anterior";
    });
  });
}

function summaryCards(result) {
  const summary = result.resumen;
  return [
    card("Zonas evaluadas", summary.zonas_evaluadas),
    card("Resultados", summary.resultados_generados),
    card("Zonas con déficit", summary.zonas_con_deficit),
    card("Zonas con exceso", summary.zonas_con_exceso),
    card("Reasignaciones", summary.reasignaciones)
  ].join("");
}

function renderCurrentAnalysis(result) {
  $("#current-analysis-cards").innerHTML = [
    card("Estado", "Sin balance energético"),
    card("Zonas analizadas", result.resumen.zonas_evaluadas),
    card("Déficits actuales", result.resumen.zonas_con_deficit),
    card("Excesos actuales", result.resumen.zonas_con_exceso),
    card("Luz artificial", "No asignada")
  ].join("");
  $("#current-status").textContent = "Condición actual cargada";
  state.result = result;
  renderFloorSelectors(result.layout);
}

function renderGenerator(generator) {
  if (!generator) {
    $("#generator-panel").innerHTML = `<div class="generator-card"><p class="muted">El balance energético todavía no se ha ejecutado.</p></div>`;
    return;
  }
  const percent = Math.min(100, Number(generator.porcentaje_usado || 0));
  const statusClass = generator.estado === "OPERACION_NORMAL" ? "normal" : generator.estado === "ALTA_DEMANDA" ? "warning" : "critical";
  $("#generator-panel").innerHTML = `<div class="generator-card"><div><p class="eyebrow">Balance energético</p><h3>Estado del generador</h3><p class="muted">La barra representa la demanda máxima asignada frente a la capacidad disponible.</p></div><div class="generator-value">${percent.toFixed(1)}<span>%</span></div><div class="energy-track"><div class="energy-fill ${statusClass}" style="width:${percent}%"></div></div><div class="energy-details"><span>Capacidad: <strong>${generator.capacidad_w.toFixed(0)} W</strong></span><span>Demanda máxima: <strong>${generator.demanda_maxima_w.toFixed(0)} W</strong></span><span>Reserva: <strong>${generator.reserva_w.toFixed(0)} W</strong></span><b class="energy-status ${statusClass}">${generator.estado.replaceAll("_", " ")}</b></div></div>`;
}

function renderFloorSelectors(layout) {
  $("#floor-tower").innerHTML = layout.torres.map((tower) => `<option value="${tower.id}">${tower.id}</option>`).join("");
  updateFloorOptions();
  $("#floor-tower").onchange = updateFloorOptions;
  $("#floor-number").onchange = renderFloorPlan;
  renderFloorPlan();
}

function updateFloorOptions() {
  const tower = state.result.layout.torres.find((item) => item.id === $("#floor-tower").value) || state.result.layout.torres[0];
  $("#floor-number").innerHTML = tower.pisos.map((floor) => `<option value="${floor.numero}">Piso ${floor.numero}</option>`).join("");
  renderFloorPlan();
}

function zoneColor(zone) {
  const colors = { CONFORTABLE: "#54b981", DEFICIT_LEVE: "#ec9e43", DEFICIT_SEVERO: "#dc5965", EXCESO_LEVE: "#e3bd4e", EXCESO_SEVERO: "#965dc5", DATOS_INSUFICIENTES: "#98a6b8" };
  return colors[zone.estado] || "#98a6b8";
}

function renderFloorPlan() {
  if (!state.result || !state.result.layout) return;
  const tower = state.result.layout.torres.find((item) => item.id === $("#floor-tower").value) || state.result.layout.torres[0];
  const floor = tower.pisos.find((item) => item.numero === Number($("#floor-number").value)) || tower.pisos[0];
  const box = tower.caja;
  const width = Math.max(1, box.max_x - box.min_x);
  const height = Math.max(1, box.max_y - box.min_y);
  const scaleX = 900 / width;
  const scaleY = 500 / height;
  const shapes = floor.zonas.map((zone) => {
    const p = zone.posicion;
    const x = 50 + (p.x - box.min_x) * scaleX - p.ancho * scaleX / 2;
    const y = 40 + (p.y - box.min_y) * scaleY - p.alto * scaleY / 2;
    const w = Math.max(34, p.ancho * scaleX);
    const h = Math.max(26, p.alto * scaleY);
    return `<g class="zone-shape" data-zone-id="${zone.id}"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="7" fill="${zoneColor(zone)}" fill-opacity=".82"></rect><text x="${x + w / 2}" y="${y + h / 2}" text-anchor="middle" dominant-baseline="middle">${zone.id.replace(`${tower.id}-`, "")}</text></g>`;
  }).join("");
  $("#floor-plan").innerHTML = `<svg viewBox="0 0 1000 580" role="img" aria-label="Plano esquemático de ${tower.id}, piso ${floor.numero}"><rect class="building-outline" x="35" y="25" width="930" height="530" rx="14"></rect>${shapes}<text class="floor-label" x="50" y="570">${tower.id} · Piso ${floor.numero}</text></svg><div class="legend"><span><i class="legend-dot comfortable"></i>Confortable</span><span><i class="legend-dot deficit"></i>Déficit</span><span><i class="legend-dot excess"></i>Exceso</span></div>`;
  document.querySelectorAll(".zone-shape").forEach((shape) => shape.addEventListener("click", () => showZoneDetail(shape.dataset.zoneId)));
}

function showZoneDetail(zoneId) {
  const zone = state.result.layout.torres.flatMap((tower) => tower.pisos.flatMap((floor) => floor.zonas)).find((item) => item.id === zoneId);
  if (!zone) return;
  $("#zone-detail").innerHTML = `<strong>${escapeHtml(zone.id)}</strong><span>${escapeHtml(zone.actividad)} · Piso ${zone.piso}</span><span>Estado: <b class="inline-state">${escapeHtml(zone.estado)}</b></span><span>Promedio: ${zone.promedio_lux.toFixed(1)} lux</span>`;
}

function renderResult(result) {
  state.result = result;
  $("#results-panel").classList.remove("hidden");
  $("#result-cards").innerHTML = summaryCards(result);
  renderGenerator(result.generador);
  renderFloorSelectors(result.layout);
  $("#current-status").textContent = "Balance aplicado sobre la condición actual";
  const states = Object.entries(result.resumen.estados).map(([name, count]) => `<tr><td>${escapeHtml(name)}</td><td>${count}</td></tr>`).join("");
  $("#state-table").innerHTML = `<div class="output-block"><h3>Estados calculados</h3><table><thead><tr><th>Estado</th><th>Resultados</th></tr></thead><tbody>${states}</tbody></table></div>`;
  const recommendations = result.reasignaciones.length ? result.reasignaciones.map((item) => `<div class="recommendation"><strong>${escapeHtml(item.estado)}</strong><br>Huésped: ${escapeHtml(item.huesped_id)}<br>Habitación actual: ${escapeHtml(item.habitacion_actual)}<br>Propuesta: ${escapeHtml(item.habitacion_propuesta || "No existe alternativa")}</div>`).join("") : `<p class="muted">No se generaron recomendaciones de reasignación para este escenario.</p>`;
  $("#recommendations").innerHTML = `<div class="output-block"><h3>Recomendaciones</h3>${recommendations}</div>`;
  const rows = Object.entries(result.resumen_zonas).slice(0, 40).map(([id, data]) => `<tr><td>${escapeHtml(id)}</td><td>${data.promedio_lux.toFixed(1)}</td><td>${data.maximo_lux.toFixed(1)}</td><td>${data.pasos_deficit}</td><td>${data.pasos_confortables}</td><td>${data.energia_wh.toFixed(1)}</td></tr>`).join("");
  $("#zone-table").innerHTML = `<div class="output-block"><h3>Resumen de zonas</h3><p class="muted">Se muestran las primeras 40 zonas; el JSON contiene el detalle completo.</p><table><thead><tr><th>Zona</th><th>Promedio lux</th><th>Máximo lux</th><th>Déficit</th><th>Confort</th><th>Wh</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

async function balance() {
  const button = $("#main-balance-button");
  button.disabled = true;
  button.textContent = "Balanceando energía...";
  $("#validation-status").textContent = "Validando entradas...";
  try {
    const validation = await request("/api/validar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state.config) });
    $("#validation-status").textContent = `Entradas válidas · ${validation.zonas_generadas} zonas`;
    renderResult(await request("/api/balancear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state.config) }));
  } catch (error) {
    $("#validation-status").textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Analizar iluminación y balancear energía";
  }
}

function download(name, content, type) {
  const blob = new Blob([content], { type });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  link.click();
  URL.revokeObjectURL(link.href);
}

function downloadCsv() {
  const headers = ["zona_id", "hora", "periodo", "modo", "luz_natural", "luz_reflejada", "luz_artificial", "luz_total", "potencia_asignada", "estado"];
  const csv = [headers.join(","), ...state.result.resultados.map((row) => headers.map((header) => JSON.stringify(row[header] ?? "")).join(","))].join("\n");
  download("reporte.csv", csv, "text/csv;charset=utf-8");
}

$("#main-balance-button").addEventListener("click", balance);
$("#download-config").addEventListener("click", () => download("datos_hotel.json", JSON.stringify(state.config, null, 2), "application/json"));
$("#download-json").addEventListener("click", () => download("resultados.json", JSON.stringify(state.result, null, 2), "application/json"));
$("#download-csv").addEventListener("click", downloadCsv);

async function loadScenario() {
  try {
    const payload = await request("/api/escenario");
    renderScenario(payload);
  } catch (error) {
    $("#validation-status").textContent = error.message;
    $("#current-status").textContent = "No se pudo cargar el análisis actual";
  }
}

loadScenario();
