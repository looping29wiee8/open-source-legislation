-- Debug Helper Functions for Legislative Data Validation
-- 
-- These functions provide standardized debugging queries for tree-structured legislative data.
-- Usage: SELECT * FROM debug_node_distribution('us_az_statutes');

-- 1. Node Distribution - Most common debugging query
CREATE OR REPLACE FUNCTION debug_node_distribution(table_name text)
RETURNS TABLE(
    level_classifier text, 
    count bigint, 
    percentage numeric
) AS $$
BEGIN
    RETURN QUERY EXECUTE format('
        WITH totals AS (SELECT COUNT(*) as total FROM %I)
        SELECT 
            n.level_classifier::text, 
            COUNT(*)::bigint,
            ROUND(COUNT(*) * 100.0 / totals.total, 1)::numeric
        FROM %I n, totals
        GROUP BY n.level_classifier, totals.total
        ORDER BY COUNT(*) DESC
    ', table_name, table_name);
END;
$$ LANGUAGE plpgsql;

-- 2. Subtree by Insertion Order - Your key debugging pattern
CREATE OR REPLACE FUNCTION debug_subtree_by_insertion(table_name text, root_pattern text)
RETURNS TABLE(
    insertion_order bigint,
    depth int,
    id text,
    level_classifier text,
    node_name text,
    parent text
) AS $$
BEGIN
    RETURN QUERY EXECUTE format('
        WITH RECURSIVE tree_with_depth AS (
            -- Base case: Find root nodes matching pattern
            SELECT 
                ROW_NUMBER() OVER (ORDER BY id) as insertion_order,
                0 as depth,
                id,
                level_classifier,
                node_name,
                parent
            FROM %I
            WHERE id LIKE %L
            AND (parent IS NULL OR parent NOT LIKE %L)
            
            UNION ALL
            
            -- Recursive case: Find children
            SELECT 
                ROW_NUMBER() OVER (ORDER BY child.id) as insertion_order,
                tree_with_depth.depth + 1,
                child.id,
                child.level_classifier,
                child.node_name,
                child.parent
            FROM %I child
            INNER JOIN tree_with_depth ON child.parent = tree_with_depth.id
        )
        SELECT * FROM tree_with_depth ORDER BY insertion_order
    ', table_name, root_pattern, root_pattern, table_name);
END;
$$ LANGUAGE plpgsql;

-- 3. Content Population Check - Critical for debugging extraction issues
CREATE OR REPLACE FUNCTION debug_content_population(table_name text)
RETURNS TABLE(
    level_classifier text,
    total_nodes bigint,
    nodes_with_text bigint,
    nodes_with_citations bigint,
    text_percentage numeric,
    citation_percentage numeric
) AS $$
BEGIN
    RETURN QUERY EXECUTE format('
        SELECT 
            level_classifier::text,
            COUNT(*)::bigint as total_nodes,
            COUNT(node_text)::bigint as nodes_with_text,
            COUNT(citation)::bigint as nodes_with_citations,
            ROUND(COUNT(node_text) * 100.0 / COUNT(*), 1)::numeric as text_percentage,
            ROUND(COUNT(citation) * 100.0 / COUNT(*), 1)::numeric as citation_percentage
        FROM %I
        GROUP BY level_classifier
        ORDER BY COUNT(*) DESC
    ', table_name);
END;
$$ LANGUAGE plpgsql;

-- 4. Validate Tree Structure - Detect common hierarchy issues
CREATE OR REPLACE FUNCTION debug_tree_structure(table_name text)
RETURNS TABLE(
    issue_type text,
    count bigint,
    sample_ids text[]
) AS $$
BEGIN
    RETURN QUERY EXECUTE format('
        -- Orphaned nodes (non-corpus nodes without parents)
        SELECT 
            ''orphaned_nodes''::text as issue_type,
            COUNT(*)::bigint,
            CASE WHEN COUNT(*) > 0 
                THEN (SELECT ARRAY_AGG(id ORDER BY id) FROM (SELECT id FROM %I WHERE parent IS NULL AND level_classifier != ''corpus'' LIMIT 5) sub)
                ELSE ARRAY[]::text[]
            END
        FROM %I
        WHERE parent IS NULL AND level_classifier != ''corpus''
        
        UNION ALL
        
        -- Missing parents (parent field points to non-existent node)
        SELECT 
            ''missing_parents''::text as issue_type,
            COUNT(*)::bigint,
            CASE WHEN COUNT(*) > 0
                THEN (SELECT ARRAY_AGG(child_id ORDER BY child_id) FROM (
                    SELECT child.id as child_id
                    FROM %I child
                    LEFT JOIN %I parent_check ON child.parent = parent_check.id
                    WHERE child.parent IS NOT NULL AND parent_check.id IS NULL
                    LIMIT 5
                ) sub)
                ELSE ARRAY[]::text[]
            END
        FROM %I child
        LEFT JOIN %I parent_check ON child.parent = parent_check.id
        WHERE child.parent IS NOT NULL 
        AND parent_check.id IS NULL
        
        UNION ALL
        
        -- Duplicate IDs
        SELECT 
            ''duplicate_ids''::text as issue_type,
            COUNT(*)::bigint,
            CASE WHEN COUNT(*) > 0
                THEN (SELECT ARRAY_AGG(id ORDER BY id) FROM (
                    SELECT id FROM (
                        SELECT id, COUNT(*) as dup_count
                        FROM %I
                        GROUP BY id
                        HAVING COUNT(*) > 1
                    ) dups LIMIT 5
                ) sub)
                ELSE ARRAY[]::text[]
            END
        FROM (
            SELECT id, COUNT(*) as dup_count
            FROM %I
            GROUP BY id
            HAVING COUNT(*) > 1
        ) dups
    ', table_name, table_name, table_name, table_name, table_name, table_name, table_name, table_name);
END;
$$ LANGUAGE plpgsql;

-- 5. Path to Root - Trace any node back to corpus
CREATE OR REPLACE FUNCTION debug_path_to_root(table_name text, node_id text)
RETURNS TABLE(
    level int,
    id text,
    level_classifier text,
    node_name text
) AS $$
BEGIN
    RETURN QUERY EXECUTE format('
        WITH RECURSIVE path_trace AS (
            -- Start with the target node
            SELECT 
                0 as level,
                id,
                level_classifier,
                node_name,
                parent
            FROM %I
            WHERE id = %L
            
            UNION ALL
            
            -- Walk up to parents
            SELECT 
                path_trace.level + 1,
                parent_node.id,
                parent_node.level_classifier,
                parent_node.node_name,
                parent_node.parent
            FROM path_trace
            INNER JOIN %I parent_node ON path_trace.parent = parent_node.id
        )
        SELECT level::int, id::text, level_classifier::text, node_name::text
        FROM path_trace
        ORDER BY level
    ', table_name, node_id, table_name);
END;
$$ LANGUAGE plpgsql;

-- 6. Quick Health Check - One-stop debugging overview
CREATE OR REPLACE FUNCTION debug_quick_health(table_name text)
RETURNS TABLE(
    metric text,
    value text
) AS $$
DECLARE
    total_count bigint;
    section_count bigint;
    content_count bigint;
    orphan_count bigint;
BEGIN
    -- Get basic counts
    EXECUTE format('SELECT COUNT(*) FROM %I', table_name) INTO total_count;
    EXECUTE format('SELECT COUNT(*) FROM %I WHERE level_classifier = ''SECTION''', table_name) INTO section_count;
    EXECUTE format('SELECT COUNT(*) FROM %I WHERE level_classifier = ''SECTION'' AND node_text IS NOT NULL', table_name) INTO content_count;
    EXECUTE format('SELECT COUNT(*) FROM %I WHERE parent IS NULL AND level_classifier != ''corpus''', table_name) INTO orphan_count;
    
    -- Return structured results
    RETURN QUERY VALUES
        ('total_nodes', total_count::text),
        ('total_sections', section_count::text),
        ('sections_with_content', content_count::text),
        ('content_percentage', CASE WHEN section_count > 0 THEN ROUND(content_count * 100.0 / section_count, 1)::text || '%' ELSE '0%' END),
        ('orphaned_nodes', orphan_count::text),
        ('health_status', CASE 
            WHEN orphan_count > 0 THEN 'CRITICAL - Orphaned nodes detected'
            WHEN content_count = 0 AND section_count > 0 THEN 'WARNING - No content extracted'
            WHEN total_count < 10 THEN 'WARNING - Very few nodes created'
            ELSE 'OK'
        END);
END;
$$ LANGUAGE plpgsql;

-- Usage Examples:
-- SELECT * FROM debug_quick_health('us_az_statutes');
-- SELECT * FROM debug_node_distribution('us_az_statutes');
-- SELECT * FROM debug_subtree_by_insertion('us_az_statutes', 'us/az/statutes/title=1%');
-- SELECT * FROM debug_content_population('us_az_statutes');
-- SELECT * FROM debug_tree_structure('us_az_statutes');
-- SELECT * FROM debug_path_to_root('us_az_statutes', 'us/az/statutes/title=1/chapter=1/article=1/section=1-101');