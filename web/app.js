const state = { config: null, result: null };

const $ = (selector) => document.querySelector(selector);

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "No se pudo completar la solicitud");
  return payload;
}

function card(label, value) {
  return `<div class="card"><span>${label}</span><strong>${value}</strong></div>`;
}

function renderScenario(payload) {
  state.config = payload.config;
  $("#json-input").value = JSON.stringify(payload.config, null, 2);
  const summary = payload.resumen_inicial;
  $("#scenario-cards").innerHTML = [
    card("Hotel", summary.hotel_id),
    card("Torres", summary.torres.length),
    card("Huéspedes", summary.huespedes),
    card("Generador", `${summary.generador_kw} kW`),
    card("Perfil climático", summary.perfil_climatico)
  ].join("");
  const towers = summary.torres.map((tower) => `<tr><td>${tower.id}</td><td>${tower.pisos}</td><td>${tower.habitaciones}</td><td>${tower.habitaciones_ocupadas}</td><td>${tower.zonas_comunes}</td></tr>`).join("");
  const activities = Object.entries(summary.actividades).map(([name, count]) => `<tr><td>${name}</td><td>${count}</td></tr>`).join("");
  $("#scenario-tables").innerHTML = `<div><h3>Torres</h3><table><thead><tr><th>ID</th><th>Pisos</th><th>Habitaciones</th><th>Ocupadas</th><th>Zonas comunes</th></tr></thead><tbody>${towers}</tbody></table></div><div><h3>Actividades</h3><table><thead><tr><th>Actividad</th><th>Cantidad</th></tr></thead><tbody>${activities}</tbody></table></div>`;
  $("#validation-status").textContent = "Escenario cargado";
}

async function loadScenario() {
  try {
    renderScenario(await request("/api/escenario"));
  } catch (error) {
    $("#validation-status").textContent = error.message;
  }
}

function currentConfig() {
  return JSON.parse($("#json-input").value);
}

async function validateCurrent() {
  const validation = await request("/api/validar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(currentConfig()) });
  $("#validation-status").textContent = `Válido · ${validation.zonas_generadas} zonas`;
  return validation;
}

async function refreshScenario() {
  try {
    const config = currentConfig();
    const validation = await request("/api/validar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) });
    renderScenario({ config, resumen_inicial: validation.resumen });
  } catch (error) {
    $("#validation-status").textContent = error.message;
  }
}

function resultCard(label, value) {
  return card(label, typeof value === "number" ? value.toLocaleString("es-CO", { maximumFractionDigits: 2 }) : value);
}

function renderResult(result) {
  state.result = result;
  const summary = result.resumen;
  $("#results-panel").classList.remove("hidden");
  $("#result-cards").innerHTML = [
    resultCard("Zonas evaluadas", summary.zonas_evaluadas),
    resultCard("Resultados", summary.resultados_generados),
    resultCard("Potencia máxima", `${summary.potencia_maxima_w.toFixed(1)} W`),
    resultCard("Energía", `${summary.energia_total_wh.toFixed(1)} Wh`),
    resultCard("Zonas con déficit", summary.zonas_con_deficit),
    resultCard("Zonas con exceso", summary.zonas_con_exceso),
    resultCard("Reasignaciones", summary.reasignaciones)
  ].join("");
  const states = Object.entries(summary.estados).map(([name, count]) => `<tr><td>${name}</td><td>${count}</td></tr>`).join("");
  $("#state-table").innerHTML = `<div class="output-block"><h3>Estados calculados</h3><table><thead><tr><th>Estado</th><th>Resultados</th></tr></thead><tbody>${states}</tbody></table></div>`;
  const recommendations = result.reasignaciones.length ? result.reasignaciones.map((item) => `<div class="recommendation"><strong>${item.estado}</strong><br>Huésped: ${item.huesped_id}<br>Habitación actual: ${item.habitacion_actual}<br>Propuesta: ${item.habitacion_propuesta || "No existe alternativa"}</div>`).join("") : `<p class="muted">No se generaron recomendaciones de reasignación.</p>`;
  $("#recommendations").innerHTML = `<div class="output-block"><h3>Recomendaciones</h3>${recommendations}</div>`;
  const rows = Object.entries(result.resumen_zonas).slice(0, 40).map(([id, data]) => `<tr><td>${id}</td><td>${data.promedio_lux.toFixed(1)}</td><td>${data.maximo_lux.toFixed(1)}</td><td>${data.pasos_deficit}</td><td>${data.pasos_confortables}</td><td>${data.energia_wh.toFixed(1)}</td></tr>`).join("");
  $("#zone-table").innerHTML = `<div class="output-block"><h3>Resumen de zonas</h3><p class="muted">Se muestran las primeras 40 zonas; el JSON contiene el detalle completo.</p><table><thead><tr><th>Zona</th><th>Promedio lux</th><th>Máximo lux</th><th>Déficit</th><th>Confort</th><th>Wh</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

async function balance() {
  const buttons = [$("#balance-button"), $("#main-balance-button")];
  buttons.forEach((button) => { button.disabled = true; button.textContent = "Balanceando..."; });
  try {
    await validateCurrent();
    renderResult(await request("/api/balancear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(currentConfig()) }));
  } catch (error) {
    $("#validation-status").textContent = error.message;
  } finally {
    buttons.forEach((button) => { button.disabled = false; button.textContent = "Balancear y analizar"; });
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
  const rows = state.result.resultados;
  const headers = ["zona_id", "hora", "periodo", "modo", "luz_natural", "luz_reflejada", "luz_artificial", "luz_total", "potencia_asignada", "estado"];
  const csv = [headers.join(","), ...rows.map((row) => headers.map((header) => JSON.stringify(row[header] ?? "")).join(","))].join("\n");
  download("reporte.csv", csv, "text/csv;charset=utf-8");
}

$("#refresh-button").addEventListener("click", refreshScenario);
$("#balance-button").addEventListener("click", balance);
$("#main-balance-button").addEventListener("click", balance);
$("#download-json").addEventListener("click", () => download("resultados.json", JSON.stringify(state.result, null, 2), "application/json"));
$("#download-csv").addEventListener("click", downloadCsv);
loadScenario();
