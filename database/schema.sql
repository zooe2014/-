PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS personal_settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    taste_level TEXT NOT NULL DEFAULT 'medium'
        CHECK (taste_level IN ('light', 'medium', 'strong')),
    eats_spicy INTEGER NOT NULL DEFAULT 0 CHECK (eats_spicy IN (0, 1)),
    default_servings INTEGER NOT NULL DEFAULT 2 CHECK (default_servings > 0),
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL
        CHECK (category IN ('appliance', 'cookware', 'tool'))
);

CREATE TABLE IF NOT EXISTS user_equipment (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, equipment_id)
);

CREATE TABLE IF NOT EXISTS ingredients (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    aliases_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(aliases_json)),
    grams_per_ml TEXT,
    density_quality TEXT NOT NULL DEFAULT 'unknown'
        CHECK (density_quality IN ('verified', 'estimated', 'unknown')),
    CHECK ((grams_per_ml IS NULL AND density_quality = 'unknown') OR
           (grams_per_ml IS NOT NULL AND CAST(grams_per_ml AS REAL) > 0
            AND density_quality IN ('verified', 'estimated')))
);

CREATE TABLE IF NOT EXISTS seasonings (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    grams_per_ml TEXT,
    density_quality TEXT NOT NULL DEFAULT 'unknown'
        CHECK (density_quality IN ('verified', 'estimated', 'unknown')),
    CHECK ((grams_per_ml IS NULL AND density_quality = 'unknown') OR
           (grams_per_ml IS NOT NULL AND CAST(grams_per_ml AS REAL) > 0
            AND density_quality IN ('verified', 'estimated')))
);

CREATE TABLE IF NOT EXISTS ingredient_substitutions (
    source_ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    substitute_ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    usage_note TEXT NOT NULL,
    cooking_adjustment TEXT,
    PRIMARY KEY (source_ingredient_id, substitute_ingredient_id),
    CHECK (source_ingredient_id <> substitute_ingredient_id)
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    cuisine_type TEXT NOT NULL CHECK (cuisine_type IN ('chinese', 'western')),
    description TEXT NOT NULL,
    cook_time_min INTEGER NOT NULL CHECK (cook_time_min > 0),
    base_servings INTEGER NOT NULL CHECK (base_servings > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    quantity_value TEXT NOT NULL CHECK (CAST(quantity_value AS REAL) > 0),
    unit TEXT NOT NULL CHECK (unit IN ('g', 'ml', 'piece')),
    is_required INTEGER NOT NULL DEFAULT 1 CHECK (is_required IN (0, 1)),
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    preparation_note TEXT,
    PRIMARY KEY (recipe_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS recipe_seasonings (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    seasoning_id INTEGER NOT NULL REFERENCES seasonings(id),
    quantity_value TEXT NOT NULL CHECK (CAST(quantity_value AS REAL) > 0),
    unit TEXT NOT NULL CHECK (unit IN ('g', 'ml', 'tsp', 'tbsp')),
    is_required INTEGER NOT NULL DEFAULT 1 CHECK (is_required IN (0, 1)),
    taste_adjustable INTEGER NOT NULL DEFAULT 1 CHECK (taste_adjustable IN (0, 1)),
    PRIMARY KEY (recipe_id, seasoning_id)
);

CREATE TABLE IF NOT EXISTS recipe_equipment (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id),
    requirement_group INTEGER NOT NULL DEFAULT 1 CHECK (requirement_group > 0),
    PRIMARY KEY (recipe_id, equipment_id)
);

CREATE TABLE IF NOT EXISTS recipe_steps (
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL CHECK (step_number > 0),
    instruction TEXT NOT NULL,
    duration_min INTEGER CHECK (duration_min IS NULL OR duration_min > 0),
    PRIMARY KEY (recipe_id, step_number)
);

CREATE TABLE IF NOT EXISTS recipe_favorites (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, recipe_id)
);

CREATE TABLE IF NOT EXISTS search_requests (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cuisine_filter TEXT NOT NULL DEFAULT 'any'
        CHECK (cuisine_filter IN ('any', 'chinese', 'western')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS search_request_ingredients (
    search_request_id INTEGER NOT NULL REFERENCES search_requests(id) ON DELETE CASCADE,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    PRIMARY KEY (search_request_id, ingredient_id)
);

CREATE TABLE IF NOT EXISTS search_request_seasonings (
    search_request_id INTEGER NOT NULL REFERENCES search_requests(id) ON DELETE CASCADE,
    seasoning_id INTEGER NOT NULL REFERENCES seasonings(id),
    PRIMARY KEY (search_request_id, seasoning_id)
);

CREATE TABLE IF NOT EXISTS search_request_equipment (
    search_request_id INTEGER NOT NULL REFERENCES search_requests(id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipment(id),
    PRIMARY KEY (search_request_id, equipment_id)
);

CREATE INDEX IF NOT EXISTS idx_ingredients_category_name
    ON ingredients(category, name);
CREATE INDEX IF NOT EXISTS idx_seasonings_category_name
    ON seasonings(category, name);
CREATE INDEX IF NOT EXISTS idx_recipes_cuisine_time
    ON recipes(cuisine_type, cook_time_min);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_ingredient
    ON recipe_ingredients(ingredient_id, recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_seasonings_seasoning
    ON recipe_seasonings(seasoning_id, recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_equipment_equipment
    ON recipe_equipment(equipment_id, recipe_id);

