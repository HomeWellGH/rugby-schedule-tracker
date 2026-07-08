function escapeHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function lineupRows(players) {
  return players.map((p) => `
    <tr>
      <td>${p.jersey ?? "-"}</td>
      <td>${escapeHtml(p.name)}${p.captain ? ' <span class="captain-badge">C</span>' : ""}</td>
      <td>${escapeHtml(p.position || "-")}</td>
      <td>${p.caps ?? "?"}</td>
      <td>${escapeHtml(p.club || "?")}</td>
    </tr>`).join("");
}

function lineupTable(nationName, lineup, announced, asOf) {
  if (!announced || !lineup || lineup.length === 0) {
    return `<div class="squad-block">
      <h4>${escapeHtml(nationName)}</h4>
      <p class="no-squad">Not yet announced. Unions typically confirm the matchday 23 two to four days before kickoff -- check back closer to the game.</p>
    </div>`;
  }
  const starters = lineup.filter((p) => p.jersey !== null && p.jersey <= 15);
  const bench = lineup.filter((p) => p.jersey !== null && p.jersey > 15);
  const header = `<thead><tr><th>#</th><th>Player</th><th>Position</th><th>Caps</th><th>Club</th></tr></thead>`;
  return `<div class="squad-block">
    <h4>${escapeHtml(nationName)}</h4>
    <p class="as-of">Caps/club as of ${asOf ? escapeHtml(asOf) : "latest Wikipedia update"}</p>
    <table class="squad-table">
      ${header}
      <tbody>
        <tr class="group-row"><td colspan="5">Starting XV</td></tr>
        ${lineupRows(starters)}
        <tr class="group-row"><td colspan="5">Replacements</td></tr>
        ${lineupRows(bench)}
      </tbody>
    </table>
  </div>`;
}

function fixtureCard(fx) {
  const favClass = fx.is_favorite ? " is-favorite" : "";
  return `
  <article class="fixture-card${favClass}">
    <div class="fixture-top">
      <span class="matchup">${escapeHtml(fx.home)} vs ${escapeHtml(fx.away)}</span>
      <span class="competition-badge">${escapeHtml(fx.competition)}</span>
    </div>
    <dl class="fixture-meta">
      <dt>Kickoff</dt><dd>${escapeHtml(fx.kickoff_local || "TBA")}</dd>
      <dt>Venue</dt><dd>${escapeHtml(fx.venue || "TBA")}</dd>
      <dt>US broadcast</dt><dd>${escapeHtml(fx.broadcast_us || "TBA")}</dd>
    </dl>
    <details class="squad-toggle" ${fx.is_favorite ? "open" : ""}>
      <summary>Matchday 23, caps &amp; club</summary>
      <div class="squads-wrap">
        ${lineupTable(fx.home, fx.home_lineup, fx.home_lineup_announced, fx.caps_club_as_of?.[fx.home])}
        ${lineupTable(fx.away, fx.away_lineup, fx.away_lineup_announced, fx.caps_club_as_of?.[fx.away])}
      </div>
    </details>
  </article>`;
}

async function main() {
  const res = await fetch("data/schedule.json", { cache: "no-store" });
  if (!res.ok) {
    document.getElementById("generated-note").textContent =
      "Couldn't load schedule data. Run scripts/build_schedule.py or wait for the next scheduled update.";
    return;
  }
  const data = await res.json();

  document.getElementById("page-title").textContent = `${data.favorite_team} Rugby Tracker`;
  document.getElementById("favorite-heading").textContent = `${data.favorite_team} Schedule`;
  document.getElementById("generated-note").textContent =
    `Updated ${new Date(data.generated_at).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })} - times shown in ${data.timezone.replace("_", " ")}`;

  const favorites = data.fixtures.filter((f) => f.is_favorite);
  const others = data.fixtures.filter((f) => !f.is_favorite);

  document.getElementById("favorite-fixtures").innerHTML =
    favorites.length ? favorites.map(fixtureCard).join("") : `<p class="muted">No upcoming ${escapeHtml(data.favorite_team)} fixtures in the current window.</p>`;
  document.getElementById("tier1-fixtures").innerHTML =
    others.length ? others.map(fixtureCard).join("") : `<p class="muted">No other Tier 1 fixtures in the current window.</p>`;

  document.getElementById("empty-state").hidden = data.fixtures.length > 0;

  document.getElementById("caveats-list").innerHTML =
    (data.caveats || []).map((c) => `<li>${escapeHtml(c)}</li>`).join("");
}

main().catch((err) => {
  console.error(err);
  document.getElementById("generated-note").textContent = "Failed to load schedule data.";
});
