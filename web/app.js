const state = { config: null, result: null, current: null, selectedZoneId: null };
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

function infoIcon(tooltipText) {
  return `<span class="info-icon" tabindex="0" title="">!<span class="tooltip-box">${escapeHtml(tooltipText)}</span></span>`;
}

function card(label, value, tooltip = null) {
  const icon = tooltip ? infoIcon(tooltip) : "";
  return `<div class="card"><div class="card-header-with-tooltip"><span>${escapeHtml(label)}</span>${icon}</div><strong class="num">${escapeHtml(value)}</strong></div>`;
}

const STATE_META = {
  CONFORTABLE: { cls: "good", label: "Confortable", dot: "🟢" },
  DEFICIT_LEVE: { cls: "deficit-leve", label: "Déficit leve", dot: "🔵" },
  DEFICIT_SEVERO: { cls: "deficit-severo", label: "Déficit severo", dot: "🔵" },
  EXCESO_LEVE: { cls: "exceso-leve", label: "Exceso leve", dot: "🔴" },
  EXCESO_SEVERO: { cls: "exceso-severo", label: "Exceso severo", dot: "🔴" },
  DATOS_INSUFICIENTES: { cls: "sin-datos", label: "Datos insuficientes", dot: "⚪" }
};
const STATE_ORDER = ["CONFORTABLE", "DEFICIT_LEVE", "DEFICIT_SEVERO", "EXCESO_LEVE", "EXCESO_SEVERO", "DATOS_INSUFICIENTES"];
const ACTIVITY_LABELS = { HABITACION: "Habitación", COCINA: "Cocina", RECREACION: "Recreación", PARQUEADERO: "Parqueadero" };

const ACTIVITY_THEMES = {
  HABITACION: {
    name: "Habitación",
    baseColor: "#2563eb",
    fillSoft: "rgba(37, 99, 235, 0.24)",
    border: "#3b82f6",
    icon: "🛏️",
    palette: ["#1e40af", "#2563eb", "#3b82f6", "#0284c7", "#1d4ed8", "#0369a1", "#0284c7", "#38bdf8", "#1e3a8a", "#0ea5e9", "#2563eb", "#60a5fa"]
  },
  COCINA: {
    name: "Cocina",
    baseColor: "#ea580c",
    fillSoft: "rgba(234, 88, 12, 0.26)",
    border: "#f97316",
    icon: "🍳",
    palette: ["#c2410c", "#d97706", "#ea580c", "#f97316", "#b45309", "#ea580c"]
  },
  RECREACION: {
    name: "Recreación",
    baseColor: "#059669",
    fillSoft: "rgba(5, 150, 105, 0.25)",
    border: "#10b981",
    icon: "🎯",
    palette: ["#047857", "#059669", "#10b981", "#0d9488", "#0f766e", "#10b981"]
  },
  PARQUEADERO: {
    name: "Parqueadero",
    baseColor: "#64748b",
    fillSoft: "rgba(100, 116, 139, 0.28)",
    border: "#94a3b8",
    icon: "🚗",
    palette: ["#475569", "#64748b", "#334155", "#94a3b8"]
  }
};

function stateInfo(estado) {
  return STATE_META[estado] || STATE_META.DATOS_INSUFICIENTES;
}

function activityLabel(activity) {
  return ACTIVITY_LABELS[activity] || activity;
}

function zoneLabel(zone, tower) {
  return zone.id.replace(`${tower.id}-`, "");
}

function input(path, value, type = "number", step = "0.1") {
  return `<input data-path="${path}" type="${type}" value="${escapeHtml(value)}" ${type === "number" ? `step="${step}"` : ""}>`;
}

function buildForms() {
  const climateOptions = Object.keys(state.config.perfiles_climaticos).map((name) => `<option value="${name}" ${name === state.config.hotel.perfil_climatico ? "selected" : ""}>${name}</option>`).join("");
  $("#climate-select").innerHTML = climateOptions;
  $("#generator-capacity").value = state.config.generador.capacidad_kw;
  renderTowerForms();
  renderActivityForms();
  renderScheduleForms();
  renderMaterialForms();
  renderComfortTable();
  bindInputs();
}

function renderScenario(payload) {
  state.config = payload.config;
  state.current = payload.analisis_actual;
  buildForms();
  $("#validation-status").textContent = "Escenario cargado";
  renderCurrentAnalysis(state.current);
  $("#main-balance-button").disabled = false;
}

function renderTowerForms() {
  $("#tower-forms").innerHTML = state.config.torres.map((tower, index) => `
    <div class="tower-form">
      <strong>${escapeHtml(tower.id)}</strong>
      <div class="mini-grid">
        <label>
          <span>Pisos ${infoIcon("Número de pisos de la torre (3m por nivel). La prioridad de iluminación aumenta con la altura: 1 + 0.10·(piso - 1).")}</span>
          ${input(`torres.${index}.pisos`, tower.pisos, "number", "1")}
        </label>
        <label>
          <span>Habitaciones/piso ${infoIcon("Cantidad de habitaciones por planta (24 m² c/u) con orientación alternada Norte, Este, Sur y Oeste.")}</span>
          ${input(`torres.${index}.habitaciones_por_piso`, tower.habitaciones_por_piso, "number", "1")}
        </label>
        <label>
          <span>Habitaciones ocupadas ${infoIcon("Habitaciones con huéspedes alojados (capacidad: 2 huéspedes). Tienen prioridad preferente (factor 1.4).")}</span>
          ${input(`torres.${index}.habitaciones_ocupadas`, tower.habitaciones_ocupadas, "number", "1")}
        </label>
      </div>
    </div>
  `).join("");
}

function renderActivityForms() {
  const names = Object.keys(state.config.perfiles_iluminacion);
  $("#activity-forms").innerHTML = `<div class="activity-grid">${names.map((name) => {
    const profile = state.config.perfiles_iluminacion[name];
    const light = state.config.luminarias[name];
    return `
      <div class="activity-card">
        <h4>${activityLabel(name)}</h4>
        <div class="mini-grid">
          <label>
            <span>Mínimo (lux) ${infoIcon("Nivel mínimo admisible. Si la luz total cae por debajo, la zona entra en déficit (inhabitable).")}</span>
            ${input(`perfiles_iluminacion.${name}.minimo`, profile.minimo)}
          </label>
          <label>
            <span>Objetivo (lux) ${infoIcon("Iluminancia deseada para confort visual pleno que el generador busca suplir.")}</span>
            ${input(`perfiles_iluminacion.${name}.objetivo`, profile.objetivo)}
          </label>
          <label>
            <span>Máximo (lux) ${infoIcon("Límite superior de confort. Valores mayores se consideran exceso o riesgo de deslumbramiento.")}</span>
            ${input(`perfiles_iluminacion.${name}.maximo`, profile.maximo)}
          </label>
          <label>
            <span>Potencia W ${infoIcon("Potencia eléctrica en Watts de la luminaria (100 lm/W, CU=0.70, MF=0.80).")}</span>
            ${input(`luminarias.${name}.potencia_w`, light.potencia_w)}
          </label>
        </div>
      </div>
    `;
  }).join("")}</div>`;
}

function renderScheduleForms() {
  $("#schedule-forms").innerHTML = Object.entries(state.config.horarios).map(([name, schedule]) => `
    <div class="schedule-row">
      <strong>${activityLabel(name)} ${infoIcon("Horas de inicio y fin del modo ACTIVO (fuera de horario pasa a modo REDUCIDO: 30% de luz).")}</strong>
      ${input(`horarios.${name}.inicio_activa`, schedule.inicio_activa, "number", "1")}
      ${input(`horarios.${name}.fin_activa`, schedule.fin_activa, "number", "1")}
    </div>
  `).join("");
}

function renderMaterialForms() {
  const glass = Object.entries(state.config.vidrios).map(([name, value]) => `
    <div class="material-row">
      <strong>${name} ${infoIcon("Transmitancia visible (VLT): fracción de radiación solar luminosa exterior que ingresa a través del vidrio.")}</strong>
      ${input(`vidrios.${name}.transmitancia_visible`, value.transmitancia_visible)}
    </div>
  `).join("");
  const walls = Object.entries(state.config.paredes).map(([name, value]) => `
    <div class="material-row">
      <strong>${name} ${infoIcon("Reflectancia difusa de paredes interiores: determina la luz rebotada de primer orden según el grafo espacial.")}</strong>
      ${input(`paredes.${name}.reflectancia`, value.reflectancia)}
    </div>
  `).join("");
  $("#material-forms").innerHTML = `<p class="muted">Transmitancia visible (VLT)</p>${glass}<p class="muted">Reflectancia de superficies</p>${walls}`;
}

function renderComfortTable() {
  if (!state.config || !state.config.perfiles_iluminacion) return;
  const perfiles = state.config.perfiles_iluminacion;
  const rows = Object.entries(perfiles).map(([act, p]) => {
    const min = Number(p.minimo);
    const obj = Number(p.objetivo);
    const max = Number(p.maximo);
    const minRed = (min * 0.3).toFixed(0);
    const objRed = (obj * 0.3).toFixed(0);
    const maxRed = (max * 0.3).toFixed(0);
    return `
      <tr>
        <td><strong>${escapeHtml(activityLabel(act))} (Activa)</strong></td>
        <td><span class="comfort-pill deficit">&lt; ${(min * 0.5).toFixed(0)} lx</span></td>
        <td><span class="comfort-pill deficit">${(min * 0.5).toFixed(0)} – ${min - 1} lx</span></td>
        <td><span class="comfort-pill good">${min} – ${max} lx <small>(Obj: ${obj})</small></span></td>
        <td><span class="comfort-pill exceso">${max + 1} – ${(max * 1.25).toFixed(0)} lx</span></td>
        <td><span class="comfort-pill exceso">&gt; ${(max * 1.25).toFixed(0)} lx</span></td>
      </tr>
      ${act === "HABITACION" ? `
      <tr>
        <td><em>${escapeHtml(activityLabel(act))} (Descanso Noche / 30%)</em></td>
        <td><span class="comfort-pill deficit">&lt; ${(min * 0.15).toFixed(0)} lx</span></td>
        <td><span class="comfort-pill deficit">${(min * 0.15).toFixed(0)} – ${Number(minRed) - 1} lx</span></td>
        <td><span class="comfort-pill good">${minRed} – ${maxRed} lx <small>(Obj: ${objRed})</small></span></td>
        <td><span class="comfort-pill exceso">${Number(maxRed) + 1} – ${(max * 0.375).toFixed(0)} lx</span></td>
        <td><span class="comfort-pill exceso">&gt; ${(max * 0.375).toFixed(0)} lx</span></td>
      </tr>` : ""}
    `;
  }).join("");

  const container = $("#comfort-table-container");
  if (container) {
    container.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Actividad / Modo</th>
            <th>Déficit Severo (Inhabitable)</th>
            <th>Déficit Leve (Sub-óptimo)</th>
            <th>Confortable (Óptimo)</th>
            <th>Exceso Leve (Sobreiluminado)</th>
            <th>Exceso Severo (Deslumbramiento)</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }
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
      renderComfortTable();
    });
  });
}

function summaryCards(result) {
  const summary = result.resumen;
  return [
    card("Zonas evaluadas", summary.zonas_evaluadas, "Total de espacios del hotel modelados en el árbol físico."),
    card("Resultados", summary.resultados_generados, "Total de evaluaciones instantáneas a lo largo de 24 horas (48 pasos de 30 min)."),
    card("Zonas con déficit", summary.zonas_con_deficit, "Espacios donde la iluminación total cae bajo el umbral mínimo en algún momento."),
    card("Zonas con exceso", summary.zonas_con_exceso, "Espacios que superan el límite superior de iluminancia admisible (riesgo de deslumbramiento)."),
    card("Reasignaciones", summary.reasignaciones, "Propuestas de traslado de huéspedes desde habitaciones en déficit a habitaciones conformes.")
  ].join("");
}

function renderCurrentAnalysis(result) {
  $("#current-analysis-cards").innerHTML = [
    card("Estado", "Sin balance energético", "Condición lumínica pasiva (natural + reflejada) con el generador eléctrico apagado."),
    card("Zonas analizadas", result.resumen.zonas_evaluadas, "Total de recintos físicos modelados en ambas torres."),
    card("Déficits actuales", result.resumen.zonas_con_deficit, "Zonas donde la luz natural es insuficiente para cumplir el mínimo normativo."),
    card("Excesos actuales", result.resumen.zonas_con_exceso, "Zonas con sobreexposición a radiación solar directa sin atenuación."),
    card("Luz artificial", "No asignada", "Potencia eléctrica apagada para diagnosticar el comportamiento pasivo.")
  ].join("");
  $("#current-status").textContent = "Condición actual cargada";
  state.result = result;
  renderFloorSelectors(result.layout);
  renderSuggestions("#current-suggestions", result.sugerencias_habitabilidad, true);
}

function renderGenerator(generator) {
  if (!generator) {
    $("#generator-panel").innerHTML = `<div class="generator-card"><p class="muted">El balance energético todavía no se ha ejecutado.</p></div>`;
    return;
  }
  const percent = Math.min(100, Number(generator.porcentaje_usado || 0));
  const statusClass = generator.estado === "OPERACION_NORMAL" ? "normal" : generator.estado === "ALTA_DEMANDA" ? "warning" : "critical";
  $("#generator-panel").innerHTML = `
    <div class="generator-card">
      <div class="generator-top">
        <div>
          <p class="eyebrow">Balance energético</p>
          <h3>Estado del generador ${infoIcon("Generador eléctrico nominal de 22 kW con reserva didáctica del 20% para suplir únicamente luminarias.")}</h3>
          <p class="muted">La barra representa la demanda máxima asignada frente a la capacidad disponible.</p>
        </div>
        <div class="generator-value num">${percent.toFixed(1)}<span>%</span></div>
      </div>
      <div class="energy-track"><div class="energy-fill ${statusClass}" style="width:${percent}%"></div></div>
      <div class="energy-details">
        <span>Capacidad: <strong class="num">${generator.capacidad_w.toFixed(0)} W</strong></span>
        <span>Demanda máxima: <strong class="num">${generator.demanda_maxima_w.toFixed(0)} W</strong></span>
        <span>Reserva: <strong class="num">${generator.reserva_w.toFixed(0)} W</strong></span>
        <b class="energy-status ${statusClass}">${generator.estado.replaceAll("_", " ")}</b>
      </div>
    </div>
  `;
}

function renderFloorSelectors(layout) {
  $("#floor-tower").innerHTML = layout.torres.map((tower) => `<option value="${tower.id}">${tower.id}</option>`).join("");
  updateFloorOptions();
  $("#floor-tower").onchange = updateFloorOptions;
  $("#floor-number").onchange = renderFloorPlan;
  if ($("#plan-color-mode")) $("#plan-color-mode").onchange = renderFloorPlan;
  renderFloorPlan();
}

function updateFloorOptions() {
  const tower = state.result.layout.torres.find((item) => item.id === $("#floor-tower").value) || state.result.layout.torres[0];
  $("#floor-number").innerHTML = tower.pisos.map((floor) => `<option value="${floor.numero}">Piso ${floor.numero}</option>`).join("");
  renderFloorPlan();
}

function renderSuggestions(containerId, suggestions, isCurrent = false) {
  const container = $(containerId);
  if (!container) return;
  if (!suggestions || suggestions.length === 0) {
    container.innerHTML = `
      <div class="output-block">
        <div class="section-heading compact-heading">
          <div>
            <p class="eyebrow">Diagnóstico de Habitabilidad</p>
            <h3>Sugerencias para mejorar la habitabilidad ${infoIcon("Acciones basadas en los parámetros del PDF: reasignación, vidrios VLT, reflectancia de paredes, generador y distribución por pisos.")}</h3>
          </div>
        </div>
        <p class="muted">No se detectaron problemas de habitabilidad que requieran intervención inmediata. El edificio cumple satisfactoriamente con los niveles de confort.</p>
      </div>
    `;
    return;
  }

  const cards = suggestions.map((sug) => {
    const priorityClass = `prioridad-${(sug.prioridad || "media").toLowerCase()}`;
    const chips = sug.items && sug.items.length ? `
      <div class="suggestion-items">
        ${sug.items.map((it) => `<span class="suggestion-item-chip">${escapeHtml(it)}</span>`).join("")}
      </div>
    ` : "";
    return `
      <div class="suggestion-card ${priorityClass}">
        <div class="suggestion-top">
          <div class="suggestion-header-left">
            <span class="suggestion-icon">${sug.icono || "💡"}</span>
            <h4 class="suggestion-title">${escapeHtml(sug.titulo)}</h4>
          </div>
          <span class="suggestion-priority-tag">${escapeHtml(sug.prioridad || "MEDIA")}</span>
        </div>
        <div class="suggestion-body">
          <p><strong>Diagnóstico:</strong> ${escapeHtml(sug.diagnostico)}</p>
          <div class="suggestion-action"><strong>Acción sugerida:</strong> ${escapeHtml(sug.accion_propuesta)}</div>
          <span class="suggestion-impact">✓ <strong>Impacto estimado:</strong> ${escapeHtml(sug.impacto_esperado)}</span>
          ${chips}
        </div>
      </div>
    `;
  }).join("");

  container.innerHTML = `
    <div class="output-block">
      <div class="section-heading compact-heading">
        <div>
          <p class="eyebrow">Diagnóstico y Recomendaciones (PDF del Proyecto)</p>
          <h3>Sugerencias para mejorar la habitabilidad ${infoIcon("Opciones derivadas de los parámetros de diseño del hotel: vidrios VLT, reflectancia de muros, capacidad del generador y reasignación de habitaciones.")}</h3>
          <p class="muted">${isCurrent ? "Diagnóstico preliminar basado en la iluminación natural y reflectancia de la envolvente." : "Propuestas operativas y técnicas para resolver déficits, excesos y optimizar el confort de los huéspedes."}</p>
        </div>
      </div>
      <div class="suggestions-container">${cards}</div>
    </div>
  `;
}

function renderFloorPlan() {
  if (!state.result || !state.result.layout) return;
  const tower = state.result.layout.torres.find((item) => item.id === $("#floor-tower").value) || state.result.layout.torres[0];
  const floor = tower.pisos.find((item) => item.numero === Number($("#floor-number").value)) || tower.pisos[0];
  const colorMode = $("#plan-color-mode") ? $("#plan-color-mode").value : "synergy";

  const isTorrePequena = tower.id.toLowerCase().includes("pequena");
  const dimX = isTorrePequena ? "32.00 m" : "44.00 m";
  const dimY = isTorrePequena ? "31.35 m" : "43.00 m";

  const rooms = floor.zonas.filter((zone) => zone.actividad === "HABITACION");
  const kitchens = floor.zonas.filter((zone) => zone.actividad === "COCINA");
  const recreations = floor.zonas.filter((zone) => zone.actividad === "RECREACION");
  const parkings = floor.zonas.filter((zone) => zone.actividad === "PARQUEADERO");
  const common = floor.zonas.filter((zone) => zone.actividad !== "HABITACION");

  // Dimensiones del marco CAD
  const SVG_W = 1060;
  const SVG_H = 640;
  const BLDG_X = 120;
  const BLDG_Y = 80;
  const BLDG_W = 760;
  const BLDG_H = 470;

  // Pasillo central
  const CORR_Y = BLDG_Y + BLDG_H / 2 - 36;
  const CORR_H = 72;
  const roomH = (BLDG_H - CORR_H) / 2 - 12;

  // Función constructora de estilo de relleno y borde según modo
  function getSpaceStyle(activity, index, estado) {
    const info = stateInfo(estado);
    const theme = ACTIVITY_THEMES[activity] || ACTIVITY_THEMES.HABITACION;
    if (colorMode === "synergy") {
      const palette = theme.palette;
      const shade = palette[index % palette.length];
      return {
        fill: shade,
        fillOpacity: activity === "PARQUEADERO" ? 0.32 : 0.25,
        stroke: shade,
        strokeWidth: 2,
        cls: `act-${activity.toLowerCase()}`
      };
    } else {
      return {
        fill: "",
        fillOpacity: "",
        stroke: "",
        strokeWidth: 2,
        cls: `${info.cls} room-border`
      };
    }
  }

  // 1. HABITACIÓN CAD (AZUL)
  function roomCad(zone, x, y, w, h, isTop, index) {
    const info = stateInfo(zone.estado);
    const zLabel = zoneLabel(zone, tower);
    const luxText = `${zone.promedio_lux.toFixed(1)} lx`;
    const isSelected = state.selectedZoneId === zone.id;
    const style = getSpaceStyle("HABITACION", index, zone.estado);
    const facadeLabel = isTop ? "Fachada Norte" : "Fachada Sur";

    const winW = Math.min(w * 0.45, 60);
    const winX = x + (w - winW) / 2;
    const winY = isTop ? y : y + h;

    const doorW = 20;
    const doorX = x + 12;
    const doorY = isTop ? y + h : y;
    const doorLeafY = isTop ? doorY - doorW : doorY + doorW;
    const doorArcPath = isTop
      ? `M ${doorX + doorW} ${doorY} A ${doorW} ${doorW} 0 0 1 ${doorX} ${doorY - doorW}`
      : `M ${doorX + doorW} ${doorY} A ${doorW} ${doorW} 0 0 0 ${doorX} ${doorY + doorW}`;

    const bedW = Math.min(w * 0.42, 46);
    const bedH = Math.min(h * 0.45, 54);
    const bedX = x + w - bedW - 14;
    const bedY = isTop ? y + 14 : y + h - bedH - 14;
    const pillowW = bedW * 0.4;
    const pillowH = 10;
    const pillowY = isTop ? bedY + 3 : bedY + bedH - pillowH - 3;

    const standW = 8;
    const nookW = 24;
    const nookH = 24;
    const nookX = x + 8;
    const nookY = isTop ? y + 10 : y + h - nookH - 10;

    return `
      <g class="zone-shape ${style.cls} ${isSelected ? "selected" : ""}" data-zone-id="${zone.id}">
        <rect class="room-border ${colorMode === "confort" ? info.cls : ""}" x="${x}" y="${y}" width="${w}" height="${h}" rx="3"
          ${colorMode === "synergy" ? `fill="${style.fill}" fill-opacity="${style.fillOpacity}" stroke="${style.stroke}" stroke-width="${style.strokeWidth}"` : ""} />

        <rect class="furniture-element" x="${nookX}" y="${nookY}" width="${nookW}" height="${nookH}" rx="1"></rect>
        <text x="${nookX + nookW / 2}" y="${nookY + nookH / 2 + 1}" class="room-sub-text" fill="rgba(255,255,255,0.4)">WC</text>

        <rect class="bed-outline" x="${bedX}" y="${bedY}" width="${bedW}" height="${bedH}"></rect>
        <rect class="bed-pillow" x="${bedX + 3}" y="${pillowY}" width="${pillowW}" height="${pillowH}"></rect>
        <rect class="bed-pillow" x="${bedX + bedW - pillowW - 3}" y="${pillowY}" width="${pillowW}" height="${pillowH}"></rect>

        <rect class="furniture-element" x="${bedX - standW - 2}" y="${pillowY}" width="${standW}" height="${standW}"></rect>
        <rect class="furniture-element" x="${bedX + bedW + 2}" y="${pillowY}" width="${standW}" height="${standW}"></rect>

        <path class="door-arc" d="${doorArcPath}"></path>
        <line class="door-leaf" x1="${doorX}" y1="${doorY}" x2="${doorX}" y2="${doorLeafY}"></line>

        <line class="window-cad" x1="${winX}" y1="${winY}" x2="${winX + winW}" y2="${winY}"></line>
        <line class="window-glass" x1="${winX}" y1="${winY}" x2="${winX + winW}" y2="${winY}"></line>

        <text class="room-title-text" x="${x + w / 2}" y="${y + h / 2 - 8}">${escapeHtml(zLabel)}</text>
        <text class="room-sub-text" x="${x + w / 2}" y="${y + h / 2 + 5}">24 m² · Habitación</text>
        <rect class="status-indicator-pill ${info.cls}" x="${x + w / 2 - 32}" y="${y + h / 2 + 13}" width="64" height="15"></rect>
        <text class="room-lux-text" fill="#ffffff" x="${x + w / 2}" y="${y + h / 2 + 21}">${info.dot} ${luxText}</text>
      </g>
    `;
  }

  // 2. COCINA CAD (NARANJA)
  function kitchenCad(zone, x, y, w, h, index) {
    const info = stateInfo(zone.estado);
    const zLabel = zoneLabel(zone, tower);
    const luxText = `${zone.promedio_lux.toFixed(1)} lx`;
    const isSelected = state.selectedZoneId === zone.id;
    const style = getSpaceStyle("COCINA", index, zone.estado);

    const winW = Math.min(w * 0.5, 45);
    const winX = x + (w - winW) / 2;
    const winY = y + h;

    // Mesón de cocina con estufa y fregadero
    const counterW = w - 16;
    const counterH = 16;
    const counterX = x + 8;
    const counterY = y + 8;

    return `
      <g class="zone-shape ${style.cls} ${isSelected ? "selected" : ""}" data-zone-id="${zone.id}">
        <rect class="room-border ${colorMode === "confort" ? info.cls : ""}" x="${x}" y="${y}" width="${w}" height="${h}" rx="3"
          ${colorMode === "synergy" ? `fill="${style.fill}" fill-opacity="${style.fillOpacity}" stroke="${style.stroke}" stroke-width="${style.strokeWidth}"` : ""} />

        <rect class="stove-top" x="${counterX}" y="${counterY}" width="${counterW}" height="${counterH}" rx="1"></rect>
        <circle class="burner" cx="${counterX + 12}" cy="${counterY + 8}" r="4.5"></circle>
        <circle class="burner" cx="${counterX + 28}" cy="${counterY + 8}" r="4.5"></circle>
        <rect class="sink-basin" x="${counterX + counterW - 28}" y="${counterY + 3}" width="20" height="10" rx="1"></rect>

        <line class="window-cad" x1="${winX}" y1="${winY}" x2="${winX + winW}" y2="${winY}"></line>
        <line class="window-glass" x1="${winX}" y1="${winY}" x2="${winX + winW}" y2="${winY}"></line>

        <text class="room-title-text" x="${x + w / 2}" y="${y + h / 2 - 6}">🍳 ${escapeHtml(zLabel)}</text>
        <text class="room-sub-text" x="${x + w / 2}" y="${y + h / 2 + 7}">35 m² · Cocina</text>
        <rect class="status-indicator-pill ${info.cls}" x="${x + w / 2 - 32}" y="${y + h / 2 + 14}" width="64" height="15"></rect>
        <text class="room-lux-text" fill="#ffffff" x="${x + w / 2}" y="${y + h / 2 + 22}">${info.dot} ${luxText}</text>
      </g>
    `;
  }

  // 3. RECREACIÓN CAD (VERDE)
  function recreationCad(zone, x, y, w, h, index) {
    const info = stateInfo(zone.estado);
    const zLabel = zoneLabel(zone, tower);
    const luxText = `${zone.promedio_lux.toFixed(1)} lx`;
    const isSelected = state.selectedZoneId === zone.id;
    const style = getSpaceStyle("RECREACION", index, zone.estado);

    const winW = Math.min(w * 0.6, 65);
    const winX = x + (w - winW) / 2;
    const winY = y + h;

    const tableX = x + 24;
    const tableY = y + 24;
    const tableR = 12;

    return `
      <g class="zone-shape ${style.cls} ${isSelected ? "selected" : ""}" data-zone-id="${zone.id}">
        <rect class="room-border ${colorMode === "confort" ? info.cls : ""}" x="${x}" y="${y}" width="${w}" height="${h}" rx="3"
          ${colorMode === "synergy" ? `fill="${style.fill}" fill-opacity="${style.fillOpacity}" stroke="${style.stroke}" stroke-width="${style.strokeWidth}"` : ""} />

        <!-- Mobiliario Lounge Recreativo -->
        <circle class="lounge-table" cx="${tableX}" cy="${tableY}" r="${tableR}"></circle>
        <circle class="lounge-chair" cx="${tableX}" cy="${tableY - tableR - 4}" r="3.5"></circle>
        <circle class="lounge-chair" cx="${tableX}" cy="${tableY + tableR + 4}" r="3.5"></circle>
        <circle class="lounge-chair" cx="${tableX - tableR - 4}" cy="${tableY}" r="3.5"></circle>
        <circle class="lounge-chair" cx="${tableX + tableR + 4}" cy="${tableY}" r="3.5"></circle>

        <!-- Sillón / Sofá modular -->
        <rect class="lounge-table" x="${x + w - 42}" y="${y + 12}" width="32" height="18" rx="2"></rect>

        <line class="window-cad" x1="${winX}" y1="${winY}" x2="${winX + winW}" y2="${winY}"></line>
        <line class="window-glass" x1="${winX}" y1="${winY}" x2="${winX + winW}" y2="${winY}"></line>

        <text class="room-title-text" x="${x + w / 2}" y="${y + h / 2 - 6}">🎯 ${escapeHtml(zLabel)}</text>
        <text class="room-sub-text" x="${x + w / 2}" y="${y + h / 2 + 7}">80 m² · Recreación</text>
        <rect class="status-indicator-pill ${info.cls}" x="${x + w / 2 - 32}" y="${y + h / 2 + 14}" width="64" height="15"></rect>
        <text class="room-lux-text" fill="#ffffff" x="${x + w / 2}" y="${y + h / 2 + 22}">${info.dot} ${luxText}</text>
      </g>
    `;
  }

  // 4. PARQUEADERO CAD (GRIS)
  function parkingCad(zone, x, y, w, h, index) {
    const info = stateInfo(zone.estado);
    const zLabel = zoneLabel(zone, tower);
    const luxText = `${zone.promedio_lux.toFixed(1)} lx`;
    const isSelected = state.selectedZoneId === zone.id;
    const style = getSpaceStyle("PARQUEADERO", index, zone.estado);

    const bayW = 28;
    const bayH = 46;
    const bayY = y + 10;
    const bay1X = x + 14;
    const bay2X = bay1X + bayW + 8;
    const bay3X = bay2X + bayW + 8;

    return `
      <g class="zone-shape ${style.cls} ${isSelected ? "selected" : ""}" data-zone-id="${zone.id}">
        <rect class="room-border ${colorMode === "confort" ? info.cls : ""}" x="${x}" y="${y}" width="${w}" height="${h}" rx="3"
          ${colorMode === "synergy" ? `fill="${style.fill}" fill-opacity="${style.fillOpacity}" stroke="${style.stroke}" stroke-width="${style.strokeWidth}"` : ""} />

        <!-- Plazas demarcadas de parqueo -->
        <rect class="car-body" x="${bay1X + 4}" y="${bayY + 4}" width="${bayW - 8}" height="${bayH - 8}"></rect>
        <rect class="car-windshield" x="${bay1X + 6}" y="${bayY + 12}" width="${bayW - 12}" height="10"></rect>
        <line class="parking-stripe" x1="${bay1X}" y1="${bayY}" x2="${bay1X}" y2="${bayY + bayH}"></line>
        <line class="parking-stripe" x1="${bay1X + bayW}" y1="${bayY}" x2="${bay1X + bayW}" y2="${bayY + bayH}"></line>
        <line class="parking-stripe" x1="${bay2X + bayW}" y1="${bayY}" x2="${bay2X + bayW}" y2="${bayY + bayH}"></line>

        <text class="room-title-text" x="${x + w / 2}" y="${y + h / 2 + 6}">🚗 ${escapeHtml(zLabel)}</text>
        <text class="room-sub-text" x="${x + w / 2}" y="${y + h / 2 + 18}">450 m² · Parqueadero</text>
        <rect class="status-indicator-pill ${info.cls}" x="${x + w / 2 - 32}" y="${y + h / 2 + 25}" width="64" height="15"></rect>
        <text class="room-lux-text" fill="#ffffff" x="${x + w / 2}" y="${y + h / 2 + 33}">${info.dot} ${luxText}</text>
      </g>
    `;
  }

  let spacesTopHtml = "";
  let spacesBottomHtml = "";

  if (floor.numero === 1 && common.length > 0) {
    // PISO 1: Ala Superior = Habitaciones (Azul)
    const topW = (BLDG_W - 20) / Math.max(1, rooms.length);
    spacesTopHtml = rooms.map((zone, idx) => {
      const rx = BLDG_X + 10 + idx * topW;
      const ry = BLDG_Y + 10;
      return roomCad(zone, rx, ry, topW - 4, roomH, true, idx);
    }).join("");

    // PISO 1: Ala Inferior = Zonas Comunes (Cocina Naranja, Recreación Verde, Parqueadero Gris)
    const botY = BLDG_Y + BLDG_H - roomH - 10;
    const botW = BLDG_W - 20;

    const cookW = botW * 0.32;
    const recW = botW * 0.38;
    const parkW = botW * 0.30;

    // Cocinas
    const cWidth = cookW / Math.max(1, kitchens.length);
    const cookHtml = kitchens.map((zone, idx) => {
      const cx = BLDG_X + 10 + idx * cWidth;
      return kitchenCad(zone, cx, botY, cWidth - 3, roomH, idx);
    }).join("");

    // Recreaciones
    const rWidth = recW / Math.max(1, recreations.length);
    const recHtml = recreations.map((zone, idx) => {
      const rx = BLDG_X + 10 + cookW + idx * rWidth;
      return recreationCad(zone, rx, botY, rWidth - 3, roomH, idx);
    }).join("");

    // Parqueaderos
    const pWidth = parkW / Math.max(1, parkings.length);
    const parkHtml = parkings.map((zone, idx) => {
      const px = BLDG_X + 10 + cookW + recW + idx * pWidth;
      return parkingCad(zone, px, botY, pWidth - 3, roomH, idx);
    }).join("");

    spacesBottomHtml = cookHtml + recHtml + parkHtml;
  } else {
    // PISOS 2+: Solo Habitaciones en 2 alas perimetrales
    const halfCount = Math.ceil(rooms.length / 2);
    const topRooms = rooms.slice(0, halfCount);
    const bottomRooms = rooms.slice(halfCount);

    const topRoomW = (BLDG_W - 20) / Math.max(1, topRooms.length);
    spacesTopHtml = topRooms.map((zone, idx) => {
      const rx = BLDG_X + 10 + idx * topRoomW;
      const ry = BLDG_Y + 10;
      return roomCad(zone, rx, ry, topRoomW - 4, roomH, true, idx);
    }).join("");

    const botRoomW = (BLDG_W - 20) / Math.max(1, bottomRooms.length);
    spacesBottomHtml = bottomRooms.map((zone, idx) => {
      const rx = BLDG_X + 10 + idx * botRoomW;
      const ry = BLDG_Y + BLDG_H - roomH - 10;
      return roomCad(zone, rx, ry, botRoomW - 4, roomH, false, idx + halfCount);
    }).join("");
  }

  // Núcleo central de circulación vertical (Escaleras y 2 Ascensores)
  const coreW = 140;
  const coreH = CORR_H - 10;
  const coreX = BLDG_X + (BLDG_W - coreW) / 2;
  const coreY = CORR_Y + 5;
  const stairW = 60;
  const stairH = coreH;
  const elevW = 32;
  const elevH = coreH;

  const stairsLines = Array.from({ length: 7 }, (_, i) => {
    const lx = coreX + 6 + (i * (stairW - 12) / 6);
    return `<line class="stair-step" x1="${lx}" y1="${coreY + 4}" x2="${lx}" y2="${coreY + stairH - 4}"></line>`;
  }).join("");

  const verticalCore = `
    <!-- Núcleo Central de Circulación Vertical -->
    <g class="vertical-core">
      <!-- Escalera de Evacuación -->
      <rect class="cad-stairs" x="${coreX}" y="${coreY}" width="${stairW}" height="${stairH}" rx="2"></rect>
      ${stairsLines}
      <text x="${coreX + stairW / 2}" y="${coreY + stairH / 2}" class="room-sub-text" fill="#7fd8e8">SUBE ▲</text>

      <!-- Ascensor 1 -->
      <rect class="cad-elevator" x="${coreX + stairW + 8}" y="${coreY}" width="${elevW}" height="${elevH}" rx="2"></rect>
      <line class="elevator-cross" x1="${coreX + stairW + 8}" y1="${coreY}" x2="${coreX + stairW + 8 + elevW}" y2="${coreY + elevH}"></line>
      <line class="elevator-cross" x1="${coreX + stairW + 8 + elevW}" y1="${coreY}" x2="${coreX + stairW + 8}" y2="${coreY + elevH}"></line>
      <text x="${coreX + stairW + 8 + elevW / 2}" y="${coreY + elevH / 2}" class="room-sub-text" fill="#35c7e0">E1</text>

      <!-- Ascensor 2 -->
      <rect class="cad-elevator" x="${coreX + stairW + elevW + 12}" y="${coreY}" width="${elevW}" height="${elevH}" rx="2"></rect>
      <line class="elevator-cross" x1="${coreX + stairW + elevW + 12}" y1="${coreY}" x2="${coreX + stairW + elevW + 12 + elevW}" y2="${coreY + elevH}"></line>
      <line class="elevator-cross" x1="${coreX + stairW + elevW + 12 + elevW}" y1="${coreY}" x2="${coreX + stairW + elevW + 12}" y2="${coreY + elevH}"></line>
      <text x="${coreX + stairW + elevW + 12 + elevW / 2}" y="${coreY + elevH / 2}" class="room-sub-text" fill="#35c7e0">E2</text>
    </g>
  `;

  // Ejes Estructurales
  const axesX = [BLDG_X + 10, BLDG_X + BLDG_W * 0.25, BLDG_X + BLDG_W * 0.5, BLDG_X + BLDG_W * 0.75, BLDG_X + BLDG_W - 10];
  const axisBubblesTop = axesX.map((x, i) => `
    <line class="blueprint-axis" x1="${x}" y1="45" x2="${x}" y2="${BLDG_Y + BLDG_H + 25}"></line>
    <circle class="axis-bubble" cx="${x}" cy="35" r="11"></circle>
    <text class="axis-text" x="${x}" y="35">${i + 1}</text>
  `).join("");

  const axesY = [BLDG_Y + 10, CORR_Y + CORR_H / 2, BLDG_Y + BLDG_H - 10];
  const axisLabelsY = ["A", "B", "C"];
  const axisBubblesLeft = axesY.map((y, i) => `
    <line class="blueprint-axis" x1="85" y1="${y}" x2="${BLDG_X + BLDG_W + 20}" y2="${y}"></line>
    <circle class="axis-bubble" cx="72" cy="${y}" r="11"></circle>
    <text class="axis-text" x="72" y="${y}">${axisLabelsY[i]}</text>
  `).join("");

  // Rótulo / Cartela Arquitectónica
  const titleBlock = `
    <g class="title-block" transform="translate(${BLDG_X + BLDG_W - 260}, ${BLDG_Y + BLDG_H + 32})">
      <rect class="title-block-box" x="0" y="0" width="260" height="48" rx="4"></rect>
      <text class="title-block-text" font-weight="700" x="10" y="15">PROYECTO: HOTEL 2 TORRES BOGOTÁ</text>
      <text class="title-block-text" fill="#7fd8e8" x="10" y="29">${escapeHtml(tower.id)} · PISO ${floor.numero} ${floor.numero === 1 ? "(Zonas Comunes + Habitaciones)" : "(Planta Tipo)"}</text>
      <text class="title-block-text" fill="#8ea0c4" x="10" y="42">Capa: ${colorMode === "synergy" ? "Sinergia Cromática" : "Confort Lumínico"} · Escala 1:100</text>
    </g>
  `;

  // Brújula / Rosa de los Vientos
  const compass = `
    <g class="compass-rose" transform="translate(${BLDG_X + BLDG_W + 40}, 55)">
      <circle cx="0" cy="0" r="20" fill="#0d1b2e" stroke="var(--border-strong)" stroke-width="1.2"></circle>
      <polygon points="0,-16 5,0 0,-4" class="north-arrow-north"></polygon>
      <polygon points="0,16 5,0 0,4" class="north-arrow-south"></polygon>
      <polygon points="0,-16 -5,0 0,-4" class="north-arrow-north"></polygon>
      <polygon points="0,16 -5,0 0,4" class="north-arrow-south"></polygon>
      <text x="0" y="-22" font-family="var(--font-mono)" font-size="10" font-weight="700" fill="#ef4444" text-anchor="middle">N</text>
      <text x="0" y="29" font-family="var(--font-mono)" font-size="9" fill="#8ea0c4" text-anchor="middle">S</text>
      <text x="24" y="3" font-family="var(--font-mono)" font-size="9" fill="#8ea0c4" text-anchor="start">E</text>
      <text x="-25" y="3" font-family="var(--font-mono)" font-size="9" fill="#8ea0c4" text-anchor="end">O</text>
    </g>
  `;

  const dimensions = `
    <!-- Cota Superior X -->
    <line class="dim-line" x1="${BLDG_X}" y1="58" x2="${BLDG_X + BLDG_W}" y2="58"></line>
    <line class="dim-line" x1="${BLDG_X}" y1="53" x2="${BLDG_X}" y2="63"></line>
    <line class="dim-line" x1="${BLDG_X + BLDG_W}" y1="53" x2="${BLDG_X + BLDG_W}" y2="63"></line>
    <text class="dim-text" x="${BLDG_X + BLDG_W / 2}" y="54">${dimX}</text>

    <!-- Cota Izquierda Y -->
    <line class="dim-line" x1="102" y1="${BLDG_Y}" x2="102" y2="${BLDG_Y + BLDG_H}"></line>
    <line class="dim-line" x1="97" y1="${BLDG_Y}" x2="107" y2="${BLDG_Y}"></line>
    <line class="dim-line" x1="97" y1="${BLDG_Y + BLDG_H}" x2="107" y2="${BLDG_Y + BLDG_H}"></line>
    <text class="dim-text" transform="rotate(-90 95 ${BLDG_Y + BLDG_H / 2})" x="95" y="${BLDG_Y + BLDG_H / 2}">${dimY}</text>
  `;

  const defs = `
    <defs>
      <pattern id="cad-grid" width="20" height="20" patternUnits="userSpaceOnUse">
        <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(53, 199, 224, 0.04)" stroke-width="0.8"></path>
        <path d="M 100 0 L 0 0 0 100" fill="none" stroke="rgba(53, 199, 224, 0.08)" stroke-width="1.2"></path>
      </pattern>
      <pattern id="hatch-sin-datos" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="7" height="7" class="hatch-bg"></rect>
        <line x1="0" y1="0" x2="0" y2="7" class="hatch-line"></line>
      </pattern>
    </defs>
  `;

  $("#floor-plan").innerHTML = `
    <svg viewBox="0 0 ${SVG_W} ${SVG_H}" role="img" aria-label="Plano arquitectónico de ${tower.id}, piso ${floor.numero}">
      ${defs}
      <rect width="${SVG_W}" height="${SVG_H}" fill="url(#cad-grid)"></rect>

      <rect class="blueprint-border" x="16" y="16" width="${SVG_W - 32}" height="${SVG_H - 32}" rx="6"></rect>
      <rect class="blueprint-inner-border" x="22" y="22" width="${SVG_W - 44}" height="${SVG_H - 44}"></rect>

      ${axisBubblesTop}
      ${axisBubblesLeft}
      ${dimensions}

      <rect class="wall-perimeter" x="${BLDG_X}" y="${BLDG_Y}" width="${BLDG_W}" height="${BLDG_H}" rx="4"></rect>

      <rect class="corridor-area" x="${BLDG_X + 2}" y="${CORR_Y}" width="${BLDG_W - 4}" height="${CORR_H}"></rect>
      <text class="corridor-label" x="${BLDG_X + 130}" y="${CORR_Y + CORR_H / 2 + 4}">PASILLO PRINCIPAL · 2.40 m</text>
      <text class="corridor-label" x="${BLDG_X + BLDG_W - 130}" y="${CORR_Y + CORR_H / 2 + 4}">SALIDA EMERGENCIA ▶</text>

      ${verticalCore}

      ${spacesTopHtml}
      ${spacesBottomHtml}

      ${titleBlock}
      ${compass}
    </svg>
  `;

  // Leyenda en 2 grupos: Sinergia de Espacios + Confort Lumínico
  $("#floor-legend").innerHTML = `
    <div class="legend-group">
      <span class="legend-group-title">Sinergia de Espacios:</span>
      <span><i class="legend-swatch swatch-habitacion"></i>Habitación (Azul)</span>
      <span><i class="legend-swatch swatch-cocina"></i>Cocina (Naranja)</span>
      <span><i class="legend-swatch swatch-recreacion"></i>Recreación (Verde)</span>
      <span><i class="legend-swatch swatch-parqueadero"></i>Parqueadero (Gris)</span>
      <span><i class="legend-swatch swatch-circulacion"></i>Núcleo / Pasillos</span>
    </div>
    <div class="legend-group">
      <span class="legend-group-title">Confort Lumínico:</span>
      <span><i class="legend-dot good"></i>Confortable</span>
      <span><i class="legend-dot deficit-leve"></i>Déficit leve</span>
      <span><i class="legend-dot deficit-severo"></i>Déficit severo</span>
      <span><i class="legend-dot exceso-leve"></i>Exceso leve</span>
      <span><i class="legend-dot exceso-severo"></i>Exceso severo</span>
    </div>
  `;

  // Tarjetas de zonas comunes con borde y badge temático
  $("#common-zones").innerHTML = common.length ? common.map((zone) => {
    const info = stateInfo(zone.estado);
    const theme = ACTIVITY_THEMES[zone.actividad] || ACTIVITY_THEMES.HABITACION;
    return `
      <button type="button" class="common-zone-card ${info.cls}" style="border-left: 5px solid ${theme.border}; background: ${theme.fillSoft};" data-zone-id="${zone.id}">
        <span class="common-zone-top">
          <span class="common-zone-name">${theme.icon} ${escapeHtml(activityLabel(zone.actividad))}</span>
          <i class="legend-dot ${info.cls}"></i>
        </span>
        <span class="common-zone-id">${escapeHtml(zoneLabel(zone, tower))}</span>
        <span class="common-zone-state">${info.label} · <span class="num">${zone.promedio_lux.toFixed(1)} lx</span></span>
      </button>
    `;
  }).join("") : `<p class="muted">Este nivel no tiene zonas comunes registradas (ubicadas en Piso 1).</p>`;

  document.querySelectorAll(".zone-shape").forEach((shape) => {
    shape.addEventListener("click", () => {
      document.querySelectorAll(".zone-shape").forEach((s) => s.classList.remove("selected"));
      shape.classList.add("selected");
      state.selectedZoneId = shape.dataset.zoneId;
      showZoneDetail(shape.dataset.zoneId);
    });
  });
  document.querySelectorAll(".common-zone-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.selectedZoneId = btn.dataset.zoneId;
      showZoneDetail(btn.dataset.zoneId);
    });
  });
}

function showZoneDetail(zoneId) {
  const tower = state.result.layout.torres.find((t) => t.pisos.some((p) => p.zonas.some((z) => z.id === zoneId)));
  const zone = state.result.layout.torres.flatMap((t) => t.pisos.flatMap((p) => p.zonas)).find((item) => item.id === zoneId);
  if (!zone) return;
  const info = stateInfo(zone.estado);
  const theme = ACTIVITY_THEMES[zone.actividad] || ACTIVITY_THEMES.HABITACION;

  $("#zone-detail").innerHTML = `
    <strong>${theme.icon} Recinto: ${escapeHtml(zone.id)}</strong>
    <span>Ubicación: <b>${escapeHtml(tower ? tower.id : "")} · Piso ${zone.piso}</b></span>
    <span>Uso: <b style="color: ${theme.border};">${escapeHtml(activityLabel(zone.actividad))} (${zone.actividad === "HABITACION" ? "24 m²" : "Zona Común"})</b></span>
    <span>Estado: <b class="inline-state ${info.cls}">${info.dot} ${info.label}</b></span>
    <span>Iluminancia Promedio: <strong class="num">${zone.promedio_lux.toFixed(1)} lux</strong></span>
    <span>Modo Operativo: <b>${escapeHtml(zone.modo)}</b></span>
  `;
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

  renderSuggestions("#results-suggestions", result.sugerencias_habitabilidad, false);

  const recommendations = result.reasignaciones.length ? result.reasignaciones.map((item) => `
    <div class="recommendation">
      <strong>${escapeHtml(item.estado)}</strong><br>
      Huésped: <code>${escapeHtml(item.huesped_id)}</code><br>
      Habitación actual: <b>${escapeHtml(item.habitacion_actual)}</b><br>
      Propuesta alternativa: <b>${escapeHtml(item.habitacion_propuesta || "No existe alternativa en esta torre")}</b>
      ${item.score !== null ? `<br><small>Score de compatibilidad: ${item.score.toFixed(1)}</small>` : ""}
    </div>
  `).join("") : `<p class="muted">No se requirieron reasignaciones de huéspedes en este escenario (todas las habitaciones ocupadas alcanzaron niveles conformes).</p>`;
  $("#recommendations").innerHTML = `<div class="output-block"><h3>Reasignaciones operativas de huéspedes</h3>${recommendations}</div>`;

  const rows = Object.entries(result.resumen_zonas).slice(0, 40).map(([id, data]) => `<tr><td>${escapeHtml(id)}</td><td>${data.promedio_lux.toFixed(1)}</td><td>${data.maximo_lux.toFixed(1)}</td><td>${data.pasos_deficit}</td><td>${data.pasos_confortables}</td><td>${data.energia_wh.toFixed(1)}</td></tr>`).join("");
  $("#zone-table").innerHTML = `<div class="output-block"><h3>Resumen de zonas</h3><p class="muted">Se muestran las primeras 40 zonas; el reporte CSV contiene el detalle temporal completo.</p><table><thead><tr><th>Zona</th><th>Promedio lux</th><th>Máximo lux</th><th>Déficit</th><th>Confort</th><th>Wh</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

async function loadCurrentCondition() {
  const button = $("#load-scenario-button");
  button.disabled = true;
  button.textContent = "Cargando escenario...";
  $("#validation-status").textContent = "Calculando condición actual...";
  try {
    const current = await request("/api/condicion_actual", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(state.config) });
    $("#validation-status").textContent = "Escenario cargado";
    renderCurrentAnalysis(current);
    $("#main-balance-button").disabled = false;
  } catch (error) {
    $("#validation-status").textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Cargar escenario";
  }
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
    button.textContent = "Balancear energía";
  }
}

function handleUploadConfig(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      state.config = JSON.parse(reader.result);
    } catch (error) {
      $("#validation-status").textContent = "El archivo no es un JSON válido";
      return;
    }
    buildForms();
    $("#results-panel").classList.add("hidden");
    $("#validation-status").textContent = "Configuración cargada desde archivo";
    loadCurrentCondition();
  };
  reader.readAsText(file);
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

$("#load-scenario-button").addEventListener("click", loadCurrentCondition);
$("#main-balance-button").addEventListener("click", balance);
$("#download-config").addEventListener("click", () => download("datos_hotel.json", JSON.stringify(state.config, null, 2), "application/json"));
$("#download-json").addEventListener("click", () => download("resultados.json", JSON.stringify(state.result, null, 2), "application/json"));
$("#download-csv").addEventListener("click", downloadCsv);
$("#upload-config").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) handleUploadConfig(file);
  event.target.value = "";
});

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
