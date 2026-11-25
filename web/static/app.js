const API = '/api';
const state = {
  userId: 'demo-user',
  bootstrap: null,
  settings: null,
  selectedIngredients: new Set(),
  selectedSeasonings: new Set(),
  ingredientQuery: '',
  cuisine: 'any',
  servings: 2,
  page: 'search',
  previousPage: 'search',
  results: [],
  resultFilter: 'all',
  favorites: [],
  folders: [],
  favoriteFolder: 'all',
  detail: null,
  detailSource: 'search',
  detailUnit: new Map(),
  toastTimer: null,
};

const root = document.querySelector('#app');

document.querySelector('.topbar').addEventListener('click', (event) => {
  const button = event.target.closest('[data-nav="settings"]');
  if (!button) return;
  state.page = 'settings';
  render();
});

document.querySelector('.bottom-nav').addEventListener('click', async (event) => {
  const button = event.target.closest('[data-nav]');
  if (!button) return;
  state.page = button.dataset.nav;
  if (state.page === 'favorites') await refreshFavorites();
  render();
});

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `連線失敗（${response.status}）`);
  return payload;
}

function toast(message) {
  let element = document.querySelector('.toast');
  if (!element) {
    element = document.createElement('div');
    element.className = 'toast';
    document.body.append(element);
  }
  element.textContent = message;
  element.classList.add('show');
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => element.classList.remove('show'), 2300);
}

function setNav() {
  const activePage = state.page === 'detail'
    ? (state.detailSource === 'favorites' ? 'favorites' : 'search')
    : (state.page === 'results' ? 'search' : state.page);
  document.querySelectorAll('.nav-item').forEach((button) => {
    button.classList.toggle('active', button.dataset.nav === activePage);
  });
}

function currentFavoriteSlugs() {
  return new Set(state.favorites.map((recipe) => recipe.slug));
}

function foodEmoji(name) {
  if (/湯/.test(name)) return '🥣';
  if (/蛋|蛋炒/.test(name)) return '🍳';
  if (/麵/.test(name)) return '🍜';
  if (/馬鈴薯|氣炸/.test(name)) return '🥔';
  if (/菠菜|青江|高麗|蔬菜/.test(name)) return '🥬';
  if (/豆腐/.test(name)) return '🍲';
  return '🍽️';
}

function tasteLabel(level) {
  return ({ light: '清淡', medium: '適中', strong: '重口味' })[level] || '適中';
}

function cuisineLabel(value) {
  return ({ chinese: '中式', western: '西式', any: '不限' })[value] || '不限';
}

function navHeader(eyebrow, title, subtitle) {
  return `<div class="page-heading"><div class="eyebrow">${escapeHtml(eyebrow)}</div><h1 class="page-title">${escapeHtml(title)}</h1><p class="page-subtitle">${escapeHtml(subtitle)}</p></div>`;
}

function renderIngredientOptions() {
  const search = state.ingredientQuery.trim().toLocaleLowerCase();
  const ingredients = state.bootstrap.ingredients.filter((item) =>
    !search || `${item.name} ${item.category}`.toLocaleLowerCase().includes(search));
  const categories = [...new Set(ingredients.map((item) => item.category))];
  return categories.length ? categories.map((category) => `
    <div class="category-title">${escapeHtml(category)}</div>
    <div class="chip-list">${ingredients.filter((item) => item.category === category).map((item) => `
      <button class="chip ${state.selectedIngredients.has(item.id) ? 'selected' : ''}" data-ingredient="${item.id}" aria-pressed="${state.selectedIngredients.has(item.id)}">${escapeHtml(item.name)}</button>
    `).join('')}</div>
  `).join('') : '<div class="empty-filter">找不到符合的食材，可以試試別的名稱。</div>';
}

function renderSearch() {
  const selectedIngredientNames = state.bootstrap.ingredients
    .filter((item) => state.selectedIngredients.has(item.id)).map((item) => item.name);
  const selectedSeasoningNames = state.bootstrap.seasonings
    .filter((item) => state.selectedSeasonings.has(item.id)).map((item) => item.name);

  root.innerHTML = `
    <section class="hero">
      <span class="step-label">STEP 02 · 食材選擇</span>
      <div class="eyebrow">依照冰箱現有食材</div>
      <h1 class="page-title">今天想煮什麼？</h1>
      <p class="page-subtitle">勾選手邊的材料和器具，找一份現在就能開始的食譜。</p>
    </section>

    <section class="section-card">
      <div class="section-head">
        <div><h2>🥬 現有食材</h2><p>可搜尋食材名稱或分類</p></div>
        <span class="count-note">已選 ${state.selectedIngredients.size} 項</span>
      </div>
      <input class="field-search" id="ingredient-search" type="search" placeholder="搜尋食材，例如：豆腐、蔬菜" value="${escapeHtml(state.ingredientQuery)}">
      <div id="ingredient-options">${renderIngredientOptions()}</div>
      <div class="selection-summary"><span>${selectedIngredientNames.length ? `已選：${escapeHtml(selectedIngredientNames.join('、'))}` : '尚未選擇食材也可以搜尋。'}</span><button class="text-button" data-action="clear-ingredients">清除</button></div>
    </section>

    <section class="section-card">
      <div class="section-head"><div><h2>🧂 現有調味料</h2><p>只勾選家裡目前有的調味料</p></div><span class="count-note">已選 ${state.selectedSeasonings.size} 項</span></div>
      <div class="chip-list">${state.bootstrap.seasonings.map((item) => `
        <button class="chip ${state.selectedSeasonings.has(item.id) ? 'selected' : ''} ${item.is_spicy && state.selectedSeasonings.has(item.id) ? 'danger-selected' : ''}" data-seasoning="${item.id}" aria-pressed="${state.selectedSeasonings.has(item.id)}">${escapeHtml(item.name)}${item.is_spicy ? ' 🌶' : ''}</button>
      `).join('')}</div>
      <div class="selection-summary"><span>${selectedSeasoningNames.length ? `已選：${escapeHtml(selectedSeasoningNames.join('、'))}` : '調味料會另外比對並提示缺少項目。'}</span><button class="text-button" data-action="clear-seasonings">清除</button></div>
    </section>

    <section class="section-card">
      <div class="section-head"><div><h2>🍳 料理類型</h2><p>器具依照你的常備設定自動套用</p></div></div>
      <div class="choice-row">${[
        ['any', '不限'], ['chinese', '中式'], ['western', '西式'],
      ].map(([value, label]) => `<label class="choice-pill"><input type="radio" name="cuisine" value="${value}" ${state.cuisine === value ? 'checked' : ''}><span>${label}</span></label>`).join('')}</div>
      <div class="selection-summary"><span>口味：${tasteLabel(state.settings.taste_level)}${state.settings.eats_spicy ? '・吃辣' : '・不吃辣'}</span><button class="text-button" data-nav="settings">調整設定</button></div>
    </section>

    <section class="section-card">
      <div class="section-head"><div><h2>🍚 預計份數</h2><p>調味建議會按份數調整</p></div>
        <div class="servings-control"><button data-action="servings-down" aria-label="減少份數">−</button><span class="servings-value">${state.servings} 人</span><button data-action="servings-up" aria-label="增加份數">＋</button></div>
      </div>
    </section>
    <button class="primary-button search-submit" data-action="run-search">幫我找食譜 <span aria-hidden="true">→</span></button>
    <p class="helper-text">推薦依資料庫食譜、缺料情況和現有器具比對排序。</p>
  `;
}

function filterLabel(filter) {
  return ({ all: '全部推薦', complete: '食材齊全', substitute: '有替代食材', missing: '需準備材料', equipment: '器具不適用' })[filter];
}

function filteredResults() {
  return state.results.filter((recipe) => {
    if (state.resultFilter === 'complete') return recipe.ingredients_complete;
    if (state.resultFilter === 'substitute') return recipe.ingredient_status === 'substitution_available';
    if (state.resultFilter === 'missing') return recipe.missing_materials.length > 0;
    if (state.resultFilter === 'equipment') return !recipe.equipment_compatible;
    return true;
  });
}

function resultCard(recipe, favoriteSlugs) {
  const scoreClass = recipe.score >= 85 ? '' : recipe.score >= 65 ? 'medium' : 'low';
  const ingredientTags = recipe.ingredients_complete
    ? '<span class="mini-tag">✓ 食材齊全</span>'
    : recipe.ingredient_status === 'substitution_available'
      ? '<span class="mini-tag gold">↔ 可用替代食材</span>'
      : '<span class="mini-tag red">需準備材料</span>';
  const equipmentTag = recipe.equipment_compatible
    ? '<span class="mini-tag">✓ 器具適用</span>'
    : '<span class="mini-tag red">器具不適用</span>';
  const requiredMissing = recipe.missing_materials.filter((item) => item.required);
  const optionalMissing = recipe.missing_materials.filter((item) => !item.required);
  const visibleRequired = requiredMissing.slice(0, 3).map((item) => item.name);
  const visibleOptional = optionalMissing.slice(0, 2).map((item) => item.name);
  const alternatives = recipe.missing_ingredients.flatMap((item) =>
    item.available_substitutes.filter((sub) => sub.available).map((sub) => `${item.name}可用${sub.name}替代`));
  return `
    <article class="recipe-card" data-open-recipe="${escapeHtml(recipe.slug)}">
      <div class="recipe-card-top">
        <span class="food-art" aria-hidden="true">${foodEmoji(recipe.name)}</span>
        <div class="recipe-card-main">
          <div class="recipe-title-line"><h3 class="recipe-title">${escapeHtml(recipe.name)}</h3><span class="score-badge ${scoreClass}">${recipe.score} 分</span></div>
          <p class="recipe-meta">${recipe.cook_time_min} 分鐘　·　${cuisineLabel(recipe.cuisine_type)}　·　${recipe.requested_servings} 人份</p>
          <div class="tag-row">${ingredientTags}${equipmentTag}</div>
        </div>
        <button class="heart-button ${favoriteSlugs.has(recipe.slug) ? 'saved' : ''}" data-heart="${escapeHtml(recipe.slug)}" aria-label="${favoriteSlugs.has(recipe.slug) ? '取消收藏' : '收藏食譜'}">${favoriteSlugs.has(recipe.slug) ? '♥' : '♡'}</button>
      </div>
      ${recipe.missing_materials.length ? `<div class="card-divider"></div>${visibleRequired.length ? `<p class="card-note"><strong>必要：</strong>${escapeHtml(visibleRequired.join('、'))}${requiredMissing.length > 3 ? '…' : ''}</p>` : ''}${visibleOptional.length ? `<p class="card-note"><strong>可省略：</strong>${escapeHtml(visibleOptional.join('、'))}${optionalMissing.length > 2 ? '…' : ''}</p>` : ''}` : ''}
      ${alternatives.length ? `<p class="card-alternatives">↳ ${escapeHtml(alternatives.slice(0, 2).join('；'))}</p>` : ''}
      <div class="card-bottom"><span>推薦指數 ${recipe.score} / 100</span><span>查看詳情　›</span></div>
    </article>
  `;
}

function renderResults() {
  const recipes = filteredResults();
  const favoriteSlugs = currentFavoriteSlugs();
  root.innerHTML = `
    <button class="detail-back" data-action="back-search">← 修改搜尋條件</button>
    ${navHeader('STEP 03 · 推薦食譜', '找到這些料理', `依照${state.selectedIngredients.size} 項食材、${state.selectedSeasonings.size} 項調味料與目前器具排序。`)}
    <div class="result-toolbar"><span class="result-count">${recipes.length} 道符合目前篩選</span><span class="sort-label">推薦分數由高至低 ↓</span></div>
    <div class="filter-strip">${['all', 'complete', 'substitute', 'missing', 'equipment'].map((filter) => `<button class="filter-chip ${state.resultFilter === filter ? 'active' : ''}" data-result-filter="${filter}">${filterLabel(filter)}</button>`).join('')}</div>
    <div class="recipe-list">${recipes.length ? recipes.map((recipe) => resultCard(recipe, favoriteSlugs)).join('') : `
      <div class="empty-state"><div class="empty-icon">🍲</div><h3>這個分類目前沒有食譜</h3><p>試試其他分類，或回去調整食材與料理類型。</p><button class="secondary-button" data-action="back-search">調整搜尋條件</button></div>
    `}</div>
  `;
}

function renderSettings() {
  const equipmentByCategory = {
    appliance: ['家電／爐具', state.bootstrap.equipment.filter((item) => item.category === 'appliance')],
    cookware: ['鍋具', state.bootstrap.equipment.filter((item) => item.category === 'cookware')],
    tool: ['工具', state.bootstrap.equipment.filter((item) => item.category === 'tool')],
  };
  root.innerHTML = `
    ${navHeader('STEP 01 · 個人設定', '先設定你的下廚習慣', '儲存一次，搜尋時就會自動套用口味和常用器具。')}
    <section class="section-card">
      <div class="settings-group"><h3>口味濃淡</h3><p>用來調整食譜中的可調味料用量。</p>
        <div class="choice-row">${[['light','清淡'],['medium','適中'],['strong','重口味']].map(([value,label]) => `<label class="choice-pill"><input type="radio" name="taste" value="${value}" ${state.settings.taste_level === value ? 'checked' : ''}><span>${label}</span></label>`).join('')}</div>
      </div>
      <div class="settings-group"><label class="choice-pill"><input id="eats-spicy" type="checkbox" ${state.settings.eats_spicy ? 'checked' : ''}><span>🌶 我吃辣</span></label></div>
      <div class="settings-group"><h3>預設烹煮份數</h3><p>之後的調味建議會先依這個份數計算。</p>
        <div class="servings-control"><button data-action="settings-servings-down" aria-label="減少份數">−</button><span class="servings-value" id="settings-servings">${state.settings.default_servings} 人</span><button data-action="settings-servings-up" aria-label="增加份數">＋</button></div>
      </div>
    </section>
    <section class="section-card">
      <div class="section-head"><div><h2>🥘 我有的烹飪器具</h2><p>推薦時會用這份清單判斷是否能製作。</p></div></div>
      ${Object.entries(equipmentByCategory).filter(([, [, items]]) => items.length).map(([category, [label, items]]) => `
        <div class="category-title">${label}</div><div class="chip-list">${items.map((item) => `
          <button class="chip ${state.settings.equipment_ids.includes(item.id) ? 'selected' : ''}" data-setting-equipment="${item.id}" aria-pressed="${state.settings.equipment_ids.includes(item.id)}">${escapeHtml(item.name)}</button>
        `).join('')}</div>
      `).join('')}
    </section>
    <div class="settings-actions"><button class="primary-button" data-action="save-settings">儲存個人設定</button><div id="settings-hint" class="settings-hint"></div></div>
  `;
}

function renderFavorites() {
  const selectedFolder = state.favoriteFolder;
  const filtered = state.favorites.filter((recipe) => {
    if (selectedFolder === 'all') return true;
    if (selectedFolder === 'uncategorized') return recipe.folder_id == null;
    return String(recipe.folder_id) === selectedFolder;
  });
  const folderCount = new Map(state.folders.map((folder) => [String(folder.id), folder.recipe_count]));
  const folderTabs = [
    `<button class="folder-tab ${selectedFolder === 'all' ? 'active' : ''}" data-favorite-folder="all">全部（${state.favorites.length}）</button>`,
    ...state.folders.map((folder) => `<button class="folder-tab ${selectedFolder === String(folder.id) ? 'active' : ''}" data-favorite-folder="${folder.id}">${escapeHtml(folder.name)}（${folderCount.get(String(folder.id)) || 0}）</button>`),
    `<button class="folder-tab ${selectedFolder === 'uncategorized' ? 'active' : ''}" data-favorite-folder="uncategorized">未分類（${state.favorites.filter((item) => item.folder_id == null).length}）</button>`,
    '<button class="folder-add" data-action="add-folder">＋ 新增資料夾</button>',
  ];
  root.innerHTML = `
    ${navHeader('STEP 05 · 收藏食譜', '我的收藏 ♥', '把喜歡的食譜收進資料夾，想煮時再快速找出來。')}
    <div class="folder-row">${folderTabs.join('')}</div>
    <div class="recipe-list">${filtered.length ? filtered.map((recipe) => `
      <article class="recipe-card favorite-card" data-open-recipe="${escapeHtml(recipe.slug)}">
        <div class="recipe-card-top">
          <span class="food-art" aria-hidden="true">${foodEmoji(recipe.name)}</span>
          <div class="recipe-card-main">
            <h3 class="recipe-title">${escapeHtml(recipe.name)}</h3>
            <p class="recipe-meta">${recipe.cook_time_min} 分鐘　·　${cuisineLabel(recipe.cuisine_type)}</p>
            <div class="tag-row"><span class="mini-tag">已收藏</span>${recipe.folder_name ? `<span class="mini-tag gold">${escapeHtml(recipe.folder_name)}</span>` : '<span class="mini-tag neutral">未分類</span>'}</div>
          </div>
          <button class="heart-button saved" data-heart="${escapeHtml(recipe.slug)}" aria-label="取消收藏">♥</button>
        </div>
        <div class="card-bottom"><span>點擊食譜查看詳情</span>
          <select class="folder-select" data-move-favorite="${escapeHtml(recipe.slug)}" aria-label="移動到資料夾">
            <option value="">未分類</option>${state.folders.map((folder) => `<option value="${folder.id}" ${String(recipe.folder_id) === String(folder.id) ? 'selected' : ''}>${escapeHtml(folder.name)}</option>`).join('')}
          </select>
        </div>
      </article>
    `).join('') : `
      <div class="empty-state"><div class="empty-icon">♡</div><h3>${state.favorites.length ? '這個資料夾還沒有食譜' : '收藏清單還是空的'}</h3><p>在食譜卡片上點愛心，就能把喜歡的料理留在這裡。</p><button class="secondary-button" data-nav="search">去找食譜</button></div>
    `}</div>
  `;
}

function renderDetail() {
  if (!state.detail) return;
  const { recipe, ingredients, steps, equipment_groups, match, favorite_folder_id } = state.detail;
  const favorite = currentFavoriteSlugs().has(recipe.slug);
  const matched = new Set(match.matched_ingredients);
  const missingById = new Map(match.missing_ingredients.map((item) => [item.id, item]));
  const currentUnit = state.detailUnit;
  const units = [['g','克'],['tsp','茶匙'],['tbsp','湯匙'],['ml','毫升']];
  root.innerHTML = `
    <button class="detail-back" data-action="detail-back">← 返回${state.detailSource === 'favorites' ? '收藏' : '推薦結果'}</button>
    <section class="detail-hero">
      <span class="food-art" aria-hidden="true">${foodEmoji(recipe.name)}</span>
      <div><div class="eyebrow">STEP 04 · 食譜詳情</div><h1>${escapeHtml(recipe.name)}</h1><p>${recipe.cook_time_min} 分鐘　·　${match.requested_servings} 人份　·　${cuisineLabel(recipe.cuisine_type)}</p></div>
    </section>
    ${match.missing_ingredients.filter((item) => item.available_substitutes.length).map((item) => `
      <div class="substitute-banner">↔ 缺少<strong>${escapeHtml(item.name)}</strong>：${item.available_substitutes.map((sub) => `${escapeHtml(sub.name)}${sub.available ? '（你有）' : '（可準備）'}${sub.cooking_adjustment ? `，${escapeHtml(sub.cooking_adjustment)}` : ''}`).join('；')}</div>
    `).join('')}
    <section class="detail-section">
      <h2>食材準備 <small>${match.ingredients_complete ? '必要食材齊全' : '缺料已標示'}</small></h2>
      ${ingredients.map((item) => {
        const missing = missingById.get(item.ingredient_id);
        const status = !missing ? '<span class="mini-tag">手邊有</span>' : item.is_required ? '<span class="mini-tag red">必要 · 缺少</span>' : '<span class="mini-tag gold">可省略 · 缺少</span>';
        const alternatives = missing?.available_substitutes?.length ? `<span class="ingredient-note">替代：${missing.available_substitutes.map((sub) => `${escapeHtml(sub.name)}${sub.available ? '（手邊有）' : ''}`).join('、')}</span>` : '';
        return `<div class="ingredient-line ${missing && item.is_required ? 'missing' : ''}"><div><span class="ingredient-name">${escapeHtml(item.name)}</span> ${status}<span class="ingredient-note">${escapeHtml(item.preparation_note || '')}</span>${alternatives}</div><span class="ingredient-amount">${escapeHtml(item.quantity_value)} ${escapeHtml(item.unit)}</span></div>`;
      }).join('')}
    </section>
    <section class="detail-section">
      <h2>精準調味 <small>${tasteLabel(match.taste_settings.taste_level)} · ${match.taste_settings.eats_spicy ? '吃辣' : '不吃辣'}</small></h2>
      ${match.adjusted_seasonings.map((item) => {
        const chosen = currentUnit.get(item.id) || item.unit;
        const availableValue = item.equivalents[chosen];
        const amount = availableValue ?? item.amount;
        const displayUnit = availableValue ? chosen : item.unit;
        const warning = !availableValue && chosen !== item.unit ? item.unavailable_conversions[chosen] : '';
        return `<div class="seasoning-line"><div><span class="ingredient-name">${escapeHtml(item.name)}${item.spicy ? ' 🌶' : ''}</span>${item.omitted_for_preference ? '<span class="ingredient-note">依你的設定不加辣</span>' : ''}${warning ? `<span class="ingredient-note">${escapeHtml(warning)}</span>` : ''}</div><div class="seasoning-amount"><strong>${escapeHtml(amount)} ${escapeHtml(displayUnit)}</strong> <select class="detail-unit-select" data-unit-id="${item.id}" aria-label="${escapeHtml(item.name)}的顯示單位">${units.map(([unit, label]) => `<option value="${unit}" ${chosen === unit ? 'selected' : ''} ${item.equivalents[unit] === undefined ? 'disabled' : ''}>${label}</option>`).join('')}</select></div></div>`;
      }).join('')}
      <p class="helper-text">克數與體積需有該調味料的已確認密度才能互換；資料不足時保留原單位。</p>
    </section>
    <section class="detail-section">
      <h2>適用器具 <small>${match.equipment_status === 'compatible' ? '目前器具可製作' : '目前器具不適用'}</small></h2>
      ${equipment_groups.map((group, index) => `<div class="ingredient-line"><span>${index === 0 ? '熱源' : `需求 ${index + 1}`}</span><span class="ingredient-amount">${group.options.map((option) => escapeHtml(option.name)).join(' ／ ')}</span></div>`).join('')}
    </section>
    <section class="detail-section"><h2>步驟料理 <small>${steps.length} 個步驟</small></h2>
      ${steps.map((step) => `<div class="step-row"><span class="step-number">${step.step_number}</span><div class="step-text">${escapeHtml(step.instruction)}${step.duration_min ? `<span class="step-time">約 ${step.duration_min} 分鐘</span>` : ''}</div></div>`).join('')}
    </section>
    <div class="detail-actions"><button class="primary-button" data-heart="${escapeHtml(recipe.slug)}">${favorite ? '♥ 已收藏，點此取消' : '♡ 收藏這道食譜'}</button></div>
  `;
}

function render() {
  setNav();
  if (!state.bootstrap) return;
  if (state.page === 'search') renderSearch();
  else if (state.page === 'results') renderResults();
  else if (state.page === 'favorites') renderFavorites();
  else if (state.page === 'settings') renderSettings();
  else if (state.page === 'detail') renderDetail();
}

async function refreshFavorites() {
  const [favorites, folders] = await Promise.all([
    api(`/favorites?user_id=${encodeURIComponent(state.userId)}`),
    api(`/folders?user_id=${encodeURIComponent(state.userId)}`),
  ]);
  state.favorites = favorites.favorites;
  state.folders = folders.folders;
}

async function boot() {
  try {
    const data = await api(`/bootstrap?user_id=${encodeURIComponent(state.userId)}`);
    state.bootstrap = data;
    state.settings = { ...data.settings, equipment_ids: data.equipment_ids };
    state.servings = data.settings.default_servings;
    await refreshFavorites();
    render();
  } catch (error) {
    root.innerHTML = `<div class="error-card">無法載入資料：${escapeHtml(error.message)}<br><br>請在專案根目錄執行 <code>python web/server.py</code> 後重新整理。</div>`;
  }
}

async function runSearch() {
  try {
    root.innerHTML = '<div class="loading-card"><span class="loading-dot"></span>正在比對資料庫食譜…</div>';
    const payload = await api('/match', {
      method: 'POST',
      body: JSON.stringify({
        user_id: state.userId,
        ingredient_ids: [...state.selectedIngredients],
        seasoning_ids: [...state.selectedSeasonings],
        cuisine_filter: state.cuisine,
        servings: state.servings,
      }),
    });
    state.results = payload.results;
    state.resultFilter = 'all';
    state.previousPage = 'search';
    state.page = 'results';
    await refreshFavorites();
    render();
  } catch (error) {
    toast(error.message);
    render();
  }
}

async function openRecipe(slug, source = 'search') {
  try {
    const body = { slug, user_id: state.userId, servings: state.servings };
    if (source === 'search' && state.results.length) {
      body.ingredient_ids = [...state.selectedIngredients];
      body.seasoning_ids = [...state.selectedSeasonings];
    }
    const detail = await api('/recipe-detail', { method: 'POST', body: JSON.stringify(body) });
    state.previousPage = state.page;
    state.detailSource = source;
    state.detail = detail;
    state.detailUnit = new Map();
    state.page = 'detail';
    render();
  } catch (error) {
    toast(error.message);
  }
}

async function toggleFavorite(slug) {
  const saved = currentFavoriteSlugs().has(slug);
  try {
    if (saved) {
      await api(`/favorites/${encodeURIComponent(slug)}?user_id=${encodeURIComponent(state.userId)}`, { method: 'DELETE' });
      toast('已從收藏移除');
    } else {
      await api('/favorites', { method: 'POST', body: JSON.stringify({ user_id: state.userId, recipe_slug: slug, folder_id: null }) });
      toast('已收藏到未分類');
    }
    await refreshFavorites();
    render();
  } catch (error) {
    toast(error.message);
  }
}

async function moveFavorite(slug, folderValue) {
  try {
    await api('/favorites', {
      method: 'PUT',
      body: JSON.stringify({ user_id: state.userId, recipe_slug: slug, folder_id: folderValue ? Number(folderValue) : null }),
    });
    await refreshFavorites();
    render();
    toast(folderValue ? '已移動到資料夾' : '已移至未分類');
  } catch (error) {
    toast(error.message);
  }
}

root.addEventListener('input', (event) => {
  if (event.target.id === 'ingredient-search') {
    state.ingredientQuery = event.target.value;
    // Do not replace the input while an IME is composing Chinese characters.
    if (event.isComposing) return;
    const options = document.querySelector('#ingredient-options');
    if (options) options.innerHTML = renderIngredientOptions();
  }
});

root.addEventListener('compositionend', (event) => {
  if (event.target.id === 'ingredient-search') {
    state.ingredientQuery = event.target.value;
    const options = document.querySelector('#ingredient-options');
    if (options) options.innerHTML = renderIngredientOptions();
  }
});

root.addEventListener('change', async (event) => {
  if (event.target.name === 'cuisine') {
    state.cuisine = event.target.value;
  } else if (event.target.name === 'taste') {
    state.settings.taste_level = event.target.value;
  } else if (event.target.id === 'eats-spicy') {
    state.settings.eats_spicy = event.target.checked;
  } else if (event.target.dataset.moveFavorite) {
    await moveFavorite(event.target.dataset.moveFavorite, event.target.value);
  } else if (event.target.dataset.unitId) {
    const id = Number(event.target.dataset.unitId);
    const selected = event.target.value;
    // Preserve the chosen display unit across re-renders without changing stored amounts.
    state.detailUnit.set(id, selected);
    const item = state.detail.match.adjusted_seasonings.find((entry) => entry.id === id);
    const availableValue = item.equivalents[selected];
    const amount = event.target.closest('.seasoning-amount').querySelector('strong');
    if (availableValue) {
      amount.textContent = `${availableValue} ${selected}`;
      const note = event.target.closest('.seasoning-line').querySelector('.ingredient-note');
      if (note && note.textContent.includes('密度')) note.remove();
    } else {
      amount.textContent = `${item.amount} ${item.unit}`;
      let note = event.target.closest('.seasoning-line').querySelector('.conversion-note');
      if (!note) {
        note = document.createElement('span');
        note.className = 'conversion-note';
        event.target.closest('.seasoning-line').append(note);
      }
      note.textContent = item.unavailable_conversions[selected] || '此單位無法精確換算。';
    }
  }
});

root.addEventListener('click', async (event) => {
  const nav = event.target.closest('[data-nav]');
  if (nav) {
    state.page = nav.dataset.nav;
    if (state.page === 'favorites') await refreshFavorites();
    render();
    return;
  }
  const ingredient = event.target.closest('[data-ingredient]');
  if (ingredient) {
    const id = Number(ingredient.dataset.ingredient);
    state.selectedIngredients.has(id) ? state.selectedIngredients.delete(id) : state.selectedIngredients.add(id);
    renderSearch();
    return;
  }
  const seasoning = event.target.closest('[data-seasoning]');
  if (seasoning) {
    const id = Number(seasoning.dataset.seasoning);
    state.selectedSeasonings.has(id) ? state.selectedSeasonings.delete(id) : state.selectedSeasonings.add(id);
    renderSearch();
    return;
  }
  const heart = event.target.closest('[data-heart]');
  if (heart) {
    event.stopPropagation();
    await toggleFavorite(heart.dataset.heart);
    return;
  }
  const filter = event.target.closest('[data-result-filter]');
  if (filter) {
    state.resultFilter = filter.dataset.resultFilter;
    renderResults();
    return;
  }
  const folder = event.target.closest('[data-favorite-folder]');
  if (folder) {
    state.favoriteFolder = folder.dataset.favoriteFolder;
    renderFavorites();
    return;
  }
  const open = event.target.closest('[data-open-recipe]');
  if (open && !event.target.closest('select, button')) {
    await openRecipe(open.dataset.openRecipe, state.page === 'favorites' ? 'favorites' : 'search');
    return;
  }
  const action = event.target.closest('[data-action]')?.dataset.action;
  if (!action) return;
  if (action === 'run-search') await runSearch();
  else if (action === 'back-search') { state.page = 'search'; render(); }
  else if (action === 'detail-back') { state.page = state.previousPage; render(); }
  else if (action === 'clear-ingredients') { state.selectedIngredients.clear(); renderSearch(); }
  else if (action === 'clear-seasonings') { state.selectedSeasonings.clear(); renderSearch(); }
  else if (action === 'servings-down') { state.servings = Math.max(1, state.servings - 1); renderSearch(); }
  else if (action === 'servings-up') { state.servings = Math.min(20, state.servings + 1); renderSearch(); }
  else if (action === 'settings-servings-down') { state.settings.default_servings = Math.max(1, state.settings.default_servings - 1); renderSettings(); }
  else if (action === 'settings-servings-up') { state.settings.default_servings = Math.min(20, state.settings.default_servings + 1); renderSettings(); }
  else if (action === 'save-settings') await saveSettings();
  else if (action === 'add-folder') await addFolder();
});

root.addEventListener('click', async (event) => {
  const equipment = event.target.closest('[data-setting-equipment]');
  if (!equipment) return;
  const id = Number(equipment.dataset.settingEquipment);
  const index = state.settings.equipment_ids.indexOf(id);
  if (index >= 0) state.settings.equipment_ids.splice(index, 1);
  else state.settings.equipment_ids.push(id);
  renderSettings();
});

async function saveSettings() {
  const selectedTaste = document.querySelector('input[name="taste"]:checked')?.value || state.settings.taste_level;
  const eatsSpicy = document.querySelector('#eats-spicy')?.checked || false;
  state.settings.taste_level = selectedTaste;
  state.settings.eats_spicy = eatsSpicy;
  const hint = document.querySelector('#settings-hint');
  if (hint) hint.textContent = '正在儲存…';
  try {
    await api('/settings', {
      method: 'PUT',
      body: JSON.stringify({
        user_id: state.userId,
        taste_level: state.settings.taste_level,
        eats_spicy: state.settings.eats_spicy,
        default_servings: state.settings.default_servings,
        equipment_ids: state.settings.equipment_ids,
      }),
    });
    state.bootstrap.settings = { ...state.settings };
    if (hint) hint.textContent = '設定已儲存，搜尋時會自動套用。';
    toast('個人設定已儲存');
  } catch (error) {
    if (hint) { hint.textContent = error.message; hint.classList.add('error'); }
  }
}

async function addFolder() {
  const name = window.prompt('請輸入新的收藏資料夾名稱');
  if (!name) return;
  try {
    await api('/folders', { method: 'POST', body: JSON.stringify({ user_id: state.userId, name }) });
    await refreshFavorites();
    renderFavorites();
    toast('收藏資料夾已建立');
  } catch (error) {
    toast(error.message);
  }
}

boot();
