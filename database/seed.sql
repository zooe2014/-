PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

INSERT OR IGNORE INTO users (id, display_name) VALUES ('demo-user', '示範使用者');
INSERT OR IGNORE INTO personal_settings (user_id, taste_level, eats_spicy, default_servings)
VALUES ('demo-user', 'medium', 0, 2);

INSERT OR IGNORE INTO favorite_folders (id, user_id, name) VALUES
 (1, 'demo-user', '早餐'),
 (2, 'demo-user', '晚餐');

INSERT OR IGNORE INTO equipment (id, slug, name, category) VALUES
 (1, 'quick-cooker', '快煮鍋', 'appliance'),
 (2, 'gas-stove', '瓦斯爐', 'appliance'),
 (3, 'induction-cooker', '電磁爐', 'appliance'),
 (4, 'air-fryer', '氣炸鍋', 'appliance'),
 (5, 'frying-pan', '平底鍋／炒鍋', 'cookware'),
 (6, 'soup-pot', '湯鍋', 'cookware'),
 (7, 'cooking-pot', '煮麵鍋', 'cookware');

INSERT OR IGNORE INTO user_equipment (user_id, equipment_id) VALUES
 ('demo-user', 2), ('demo-user', 3), ('demo-user', 5), ('demo-user', 6), ('demo-user', 7);

INSERT OR IGNORE INTO ingredients (id, slug, name, category, aliases_json) VALUES
 (1, 'tofu', '板豆腐', '豆製品', '["豆腐"]'),
 (2, 'egg', '雞蛋', '蛋類', '["蛋"]'),
 (3, 'garlic', '蒜頭', '辛香料', '["大蒜"]'),
 (4, 'scallion', '青蔥', '辛香料', '["蔥"]'),
 (5, 'bok-choy', '青江菜', '蔬菜', '[]'),
 (6, 'tomato', '番茄', '蔬菜', '["西紅柿"]'),
 (7, 'spinach', '菠菜', '蔬菜', '[]'),
 (8, 'potato', '馬鈴薯', '根莖類', '["洋芋"]'),
 (9, 'cabbage', '高麗菜', '蔬菜', '["高麗菜"]'),
 (10, 'dried-wakame', '乾燥海帶芽', '海藻', '["海帶芽"]'),
 (11, 'noodles', '麵條', '主食', '["麵"]'),
 (12, 'water', '水', '液體', '[]'),
 (13, 'shiitake', '香菇', '菇類', '["冬菇"]'),
 (14, 'carrot', '紅蘿蔔', '蔬菜', '["胡蘿蔔"]');

INSERT OR IGNORE INTO seasonings (id, slug, name, category) VALUES
 (1, 'salt', '鹽', '基礎調味'),
 (2, 'soy-sauce', '醬油', '醬料'),
 (3, 'oyster-sauce', '蠔油', '醬料'),
 (4, 'sugar', '砂糖', '基礎調味'),
 (5, 'cooking-oil', '食用油', '油脂'),
 (6, 'sesame-oil', '香油', '油脂'),
 (7, 'miso', '味噌', '醬料'),
 (8, 'white-pepper', '白胡椒', '辛香調味'),
 (9, 'chili-flakes', '辣椒粉', '辛香調味');
UPDATE seasonings SET is_spicy = 1 WHERE slug = 'chili-flakes';

INSERT OR IGNORE INTO ingredient_substitutions
 (source_ingredient_id, substitute_ingredient_id, usage_note, cooking_adjustment) VALUES
 (5, 7, '適用於湯品或清炒；成品口感與味道會不同。', '菠菜較快熟，接近起鍋時再加入。'),
 (7, 5, '適用於湯品或清炒；成品口感與味道會不同。', '青江菜梗較厚，需比菠菜多煮約 1 至 2 分鐘。');

INSERT OR IGNORE INTO recipes (id, slug, name, cuisine_type, description, cook_time_min, base_servings) VALUES
 (1, 'garlic-tofu-egg-stir-fry', '蒜香豆腐炒蛋', 'chinese', '豆腐與雞蛋搭配蒜香快炒。', 15, 2),
 (2, 'bok-choy-egg-drop-soup', '青江菜蛋花湯', 'chinese', '以青江菜和蛋花煮成的清湯。', 12, 2),
 (3, 'soy-braised-tofu', '醬燒豆腐', 'chinese', '以醬油和蠔油燒煮入味的豆腐。', 18, 2),
 (4, 'tomato-scrambled-eggs', '番茄炒蛋', 'chinese', '番茄與炒蛋的家常料理。', 12, 2),
 (5, 'garlic-spinach', '蒜香炒菠菜', 'chinese', '蒜頭清炒菠菜。', 8, 2),
 (6, 'scallion-omelet', '青蔥煎蛋', 'chinese', '加入青蔥的簡單煎蛋。', 10, 2),
 (7, 'miso-tofu-wakame-soup', '味噌豆腐海帶芽湯', 'chinese', '味噌、豆腐與海帶芽煮成的湯品。', 15, 2),
 (8, 'air-fryer-potato-cubes', '氣炸馬鈴薯塊', 'western', '少量食用油拌勻後氣炸至表面金黃。', 25, 2),
 (9, 'cabbage-egg-stir-fry', '高麗菜炒蛋', 'chinese', '高麗菜、雞蛋與蒜頭快炒。', 15, 2),
 (10, 'soy-sesame-noodles', '醬油香油拌麵', 'chinese', '以醬油和香油拌合的簡單麵食。', 15, 2),
 (11, 'shiitake-bok-choy-soup', '香菇青江菜湯', 'chinese', '香菇與青江菜煮成的蔬菜湯。', 18, 2),
 (12, 'carrot-tofu-stir-fry', '紅蘿蔔豆腐炒', 'chinese', '紅蘿蔔與豆腐搭配醬油快炒。', 16, 2);

-- 食材：數量保存為十進位字串；piece 表示「個」或未細分計量的單位。
INSERT OR IGNORE INTO recipe_ingredients
 (recipe_id, ingredient_id, quantity_value, unit, is_required, is_primary, preparation_note) VALUES
 (1, 1, '250', 'g', 1, 1, '切小塊'), (1, 2, '2', 'piece', 1, 1, '打散'), (1, 3, '10', 'g', 1, 0, '切末'), (1, 4, '10', 'g', 0, 0, '切蔥花'),
 (2, 5, '200', 'g', 1, 1, '洗淨切段'), (2, 2, '1', 'piece', 1, 1, '打散'), (2, 4, '5', 'g', 0, 0, '切蔥花'),
 (3, 1, '300', 'g', 1, 1, '切厚片'), (3, 3, '8', 'g', 1, 0, '切末'), (3, 4, '10', 'g', 0, 0, '切段'),
 (4, 6, '250', 'g', 1, 1, '切塊'), (4, 2, '3', 'piece', 1, 1, '打散'), (4, 4, '5', 'g', 0, 0, '切蔥花'),
 (5, 7, '250', 'g', 1, 1, '洗淨'), (5, 3, '10', 'g', 1, 0, '切片'),
 (6, 2, '3', 'piece', 1, 1, '打散'), (6, 4, '20', 'g', 1, 1, '切蔥花'),
 (7, 1, '200', 'g', 1, 1, '切小塊'), (7, 10, '3', 'g', 1, 0, '泡水還原'), (7, 4, '5', 'g', 0, 0, '切蔥花'), (7, 12, '450', 'ml', 1, 0, NULL),
 (8, 8, '350', 'g', 1, 1, '切成大小一致的塊狀'),
 (9, 9, '250', 'g', 1, 1, '切絲'), (9, 2, '2', 'piece', 1, 1, '打散'), (9, 3, '5', 'g', 0, 0, '切末'),
 (10, 11, '200', 'g', 1, 1, '依包裝指示煮熟'), (10, 4, '10', 'g', 0, 0, '切蔥花'),
 (11, 13, '80', 'g', 1, 1, '切片'), (11, 5, '150', 'g', 1, 1, '洗淨切段'), (11, 12, '500', 'ml', 1, 0, NULL),
 (12, 14, '120', 'g', 1, 1, '切薄片'), (12, 1, '200', 'g', 1, 1, '切塊'), (12, 4, '5', 'g', 0, 0, '切蔥花');

-- 調味料的 g/ml/tsp/tbsp 都保留原始值；此批示範不填未經查證的密度。
INSERT OR IGNORE INTO recipe_seasonings
 (recipe_id, seasoning_id, quantity_value, unit, is_required, taste_adjustable) VALUES
 (1, 2, '10', 'ml', 1, 1), (1, 1, '1', 'g', 1, 1), (1, 5, '10', 'ml', 1, 0), (1, 9, '1', 'g', 0, 0),
 (2, 1, '2', 'g', 1, 1), (2, 8, '0.5', 'g', 0, 1),
 (3, 2, '1', 'tbsp', 1, 1), (3, 3, '2', 'tsp', 1, 1), (3, 4, '5', 'g', 1, 1), (3, 5, '8', 'ml', 1, 1),
 (4, 1, '1.5', 'g', 1, 1), (4, 4, '3', 'g', 0, 1), (4, 5, '10', 'ml', 1, 1),
 (5, 1, '1', 'g', 1, 1), (5, 5, '10', 'ml', 1, 1),
 (6, 1, '1.5', 'g', 1, 1), (6, 5, '8', 'ml', 1, 1),
 (7, 7, '30', 'g', 1, 1), (7, 8, '0.5', 'g', 0, 1),
 (8, 1, '2', 'g', 1, 1), (8, 5, '12', 'ml', 1, 1), (8, 8, '1', 'g', 0, 1),
 (9, 2, '8', 'ml', 1, 1), (9, 1, '1', 'g', 1, 1), (9, 5, '10', 'ml', 1, 1),
 (10, 2, '15', 'ml', 1, 1), (10, 6, '5', 'ml', 1, 1), (10, 4, '2', 'g', 0, 1),
 (11, 1, '1.5', 'g', 1, 1), (11, 8, '0.5', 'g', 0, 1),
 (12, 2, '8', 'ml', 1, 1), (12, 1, '1', 'g', 1, 1), (12, 5, '8', 'ml', 1, 1);

-- requirement_group 1 為可擇一的熱源；其他群組須各自符合。
INSERT OR IGNORE INTO recipe_equipment (recipe_id, equipment_id, requirement_group) VALUES
 (1, 2, 1), (1, 3, 1), (1, 5, 2),
 (2, 1, 1), (2, 2, 1), (2, 3, 1), (2, 6, 2),
 (3, 2, 1), (3, 3, 1), (3, 5, 2),
 (4, 2, 1), (4, 3, 1), (4, 5, 2),
 (5, 2, 1), (5, 3, 1), (5, 5, 2),
 (6, 2, 1), (6, 3, 1), (6, 5, 2),
 (7, 1, 1), (7, 2, 1), (7, 3, 1), (7, 6, 2),
 (8, 4, 1),
 (9, 2, 1), (9, 3, 1), (9, 5, 2),
 (10, 2, 1), (10, 3, 1), (10, 7, 2),
 (11, 1, 1), (11, 2, 1), (11, 3, 1), (11, 6, 2),
 (12, 2, 1), (12, 3, 1), (12, 5, 2);

INSERT OR IGNORE INTO recipe_steps (recipe_id, step_number, instruction, duration_min) VALUES
 (1, 1, '豆腐切塊，雞蛋打散；蒜頭切末。', 3), (1, 2, '熱鍋加入食用油，將豆腐煎至表面微黃。', 5), (1, 3, '加入蒜末與蛋液，炒至蛋熟後以醬油和鹽調味；可依是否吃辣加入辣椒粉，最後撒上青蔥。', 7),
 (2, 1, '青江菜洗淨切段，雞蛋打散。', 3), (2, 2, '湯鍋加水煮滾，放入青江菜梗煮至稍軟。', 5), (2, 3, '倒入蛋液形成蛋花，加入鹽調味，放入菜葉煮熟。', 4),
 (3, 1, '豆腐切厚片並以廚房紙巾吸去表面水分。', 3), (3, 2, '熱鍋加油，將豆腐兩面煎至金黃。', 6), (3, 3, '加入蒜末、醬油、蠔油、砂糖及少量水，小火燒至醬汁略收。', 9),
 (4, 1, '番茄切塊，雞蛋打散。', 3), (4, 2, '熱鍋加油炒熟蛋液，先盛起。', 3), (4, 3, '番茄入鍋炒軟，加入鹽與砂糖，再倒回雞蛋拌炒。', 6),
 (5, 1, '菠菜洗淨瀝乾，蒜頭切片。', 3), (5, 2, '熱鍋加油炒香蒜片，放入菠菜大火拌炒至熟，以鹽調味。', 5),
 (6, 1, '雞蛋打散，青蔥切細。', 3), (6, 2, '蛋液加入青蔥與鹽拌勻。', 2), (6, 3, '平底鍋加油，倒入蛋液煎至兩面熟透。', 5),
 (7, 1, '海帶芽泡水還原，豆腐切塊。', 5), (7, 2, '水煮滾後轉小火，加入豆腐與海帶芽。', 5), (7, 3, '關小火，以少量熱湯調開味噌後倒回鍋中；勿大火久煮。', 5),
 (8, 1, '馬鈴薯切塊、擦乾，與食用油、鹽和白胡椒拌勻。', 5), (8, 2, '放入氣炸鍋，以 190°C 氣炸約 15 至 20 分鐘，中途翻動一次。', 20),
 (9, 1, '高麗菜切絲，雞蛋打散；可選蒜頭切末。', 3), (9, 2, '熱鍋加油炒熟蛋液後盛起。', 3), (9, 3, '炒香蒜末，放入高麗菜炒軟，加入醬油和鹽，再拌回雞蛋。', 9),
 (10, 1, '煮麵鍋加水煮滾，依包裝指示煮熟麵條並瀝乾。', 10), (10, 2, '碗中混合醬油、香油與砂糖，放入熱麵拌勻。', 3), (10, 3, '撒上青蔥即可。', 2),
 (11, 1, '香菇切片，青江菜洗淨切段。', 3), (11, 2, '湯鍋加水煮滾，先放香菇煮至出味。', 10), (11, 3, '加入青江菜煮熟，以鹽和白胡椒調味。', 5),
 (12, 1, '紅蘿蔔切薄片，豆腐切塊。', 3), (12, 2, '熱鍋加油，將紅蘿蔔炒至略軟，再加入豆腐。', 8), (12, 3, '加入醬油與鹽輕輕拌炒，撒上青蔥。', 5);

INSERT OR IGNORE INTO recipe_favorites (user_id, recipe_id, folder_id) VALUES
 ('demo-user', 1, 1), ('demo-user', 2, 2);

-- 範例搜尋：示範使用者目前有豆腐、雞蛋、蒜頭、醬油、鹽和食用油。
INSERT OR IGNORE INTO search_requests (id, user_id, cuisine_filter) VALUES (1, 'demo-user', 'any');
INSERT OR IGNORE INTO search_request_ingredients (search_request_id, ingredient_id) VALUES
 (1, 1), (1, 2), (1, 3), (1, 4);
INSERT OR IGNORE INTO search_request_seasonings (search_request_id, seasoning_id) VALUES
 (1, 1), (1, 2), (1, 5);
INSERT OR IGNORE INTO search_request_equipment (search_request_id, equipment_id) VALUES
 (1, 2), (1, 3), (1, 5), (1, 6), (1, 7);

COMMIT;
