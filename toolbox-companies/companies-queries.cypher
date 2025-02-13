// `industries`get list of industries
MATCH (i:IndustryCategory) RETURN i.name as industry

// `companies` get list of companies by fulltext search
CALL db.index.fulltext.queryNodes('entity', $search, {limit: 25})
YIELD node as c, score WHERE c:Organization
AND not exists { (c)<-[:HAS_SUBSIDARY]-() }
RETURN c.id as id, c.name as name, c.summary as summary

// `companies_in_industry` get list of companies in an industry
MATCH (:IndustryCategory {name:$industry})<-[:HAS_CATEGORY]-(c)
WHERE not exists { (c)<-[:HAS_SUBSIDARY]-() }
RETURN c.id as id, c.name as name, c.summary as summary

// `articles_in_month` get list of articles titles in a time frame
match (a:Article)
where date($date) <= date(a.date) < date($date) + duration('P1M')
return a.id as id, a.author as author, a.title as title, toString(a.date) as date, a.sentiment as sentiment
limit 25

// `article` get article content and details
match (a:Article)-[:HAS_CHUNK]->(c:Chunk)
where a.id = $id
with a, c order by id(c) asc
with a, collect(c.text) as content
return a.id as id, a.author as author, a.title as title, toString(a.date) as date,
a.summary as summary, a.siteName as site, a.sentiment as sentiment, content

// `companies_in_articles` get list of companies mentioned in a list of articles
MATCH (a:Article)-[:MENTIONS]->(c)
WHERE a.id in $ids AND not exists { (c)<-[:HAS_SUBSIDARY]-() }
RETURN c.id as id, c.name as name, c.summary as summary

// `people_at_company` get people associated with an company
MATCH (c:Organization)-[role]-(p:Person) WHERE c.id = $id
RETURN replace(type(role),"HAS_","") as role, p.name as name