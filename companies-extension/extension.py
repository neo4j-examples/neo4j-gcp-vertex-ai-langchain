import os
from flask import Flask, jsonify, request
from neo4j import GraphDatabase

app = Flask(__name__)

URI = os.getenv('NEO4J_URI', 'neo4j+s://demo.neo4jlabs.com')
AUTH = (os.getenv('NEO4J_USERNAME','companies'),os.getenv('NEO4J_PASSWORD','companies'))

driver = GraphDatabase.driver(URI, auth = AUTH)

@app.route("/industries", methods=["GET"])
def industries():
    """
    List of Industry names
    """

    query = """
    MATCH (i:IndustryCategory) RETURN i.name as industry
    """
    records, _, _ = driver.execute_query(query, _database="companies")
    results = [r['industry'] for r in records]
    return jsonify({ "output": results })

@app.route("/companies", methods=["GET"])
def companies():
    """
    List of Companies (id, name, summary) by fulltext search
    """

    query = """
    CALL db.index.fulltext.queryNodes('entity', $search, {limit: 25}) 
    YIELD node as c, score WHERE c:Organization 
    AND not exists { (c)<-[:HAS_SUBSIDARY]-() }
    RETURN c.id as id, c.name as name, c.summary as summary
    """
    args = request.args
    search = args.get("search")
    records, _, _ = driver.execute_query(query, search=search, _database="companies")
    results = [{"Company": r['name'], "Id": r['id'], "Summary":r['summary']} for r in records]
    return jsonify({ "output": results })

@app.route("/companies_in_industry", methods=["GET"])
def companies_in_industry():
    """
    Companies (id, name, summary) in a given industry by `industry` name
    """
    query = """
    MATCH (:IndustryCategory {name:$industry})<-[:HAS_CATEGORY]-(c) 
    WHERE not exists { (c)<-[:HAS_SUBSIDARY]-() }
    RETURN c.id as id, c.name as name, c.summary as summary
    """
    args = request.args
    industry = args.get("industry")
    records, _, _ = driver.execute_query(query, industry=industry, _database="companies")
    results = [{"Company": r['name'], "Id": r['id'], "Summary":r['summary']} for r in records]
    return jsonify({ "output": results })

@app.route("/articles_in_month", methods=["GET"])
def articles_in_month():
    """
    List of Articles (id, author, title, date, sentiment) in a month timeframe from the given `date` (yyyy-mm-dd)
    """
    query = """
    match (a:Article)
    where date($date) <= date(a.date)  < date($date) + duration('P1M')
    return a.id as id, a.author as author, a.title as title, toString(a.date) as date, a.sentiment as sentiment
    limit 25
    """
    args = request.args
    date = args.get("date")

    records, _, _ = driver.execute_query(query, date=date, _database="companies")
    results = [{"Article": r['title'], "Id": r['id'], "Date": r['date'], "Sentiment":r['sentiment'], "Author":r['author']} for r in records]
    return jsonify({ "output": results })

@app.route("/article", methods=["GET"])
def article():
    """
    Single Article details (id, author, title, date, sentiment, site, summary, content) by article id
    """

    query = """
    match (a:Article)-[:HAS_CHUNK]->(c:Chunk)
    where a.id = $id
    with a, c order by id(c) asc
    with a, collect(c.text) as content
    return a.id as id, a.author as author, a.title as title, toString(a.date) as date, 
    a.summary as summary, a.siteName as site, a.sentiment as sentiment, content
    """
    args = request.args
    id = args.get("id")

    records, _, _ = driver.execute_query(query, id=id, _database="companies")
    results = [{"Article": r['title'], "Id": r['id'], "Date": r['date'], "Sentiment":r['sentiment'], "Author":r['author'], 
                "Site": r['site'], "Summary": r['summary'], "Content": r['content']} for r in records]
    return jsonify({ "output": results })

@app.route("/companies_in_articles", methods=["GET"])
def companies_in_articles():
    """
    Companies (id, name, summary) mentioned in articles by list of article ids
    """

    query = """
    MATCH (a:Article)-[:MENTIONS]->(c)
    WHERE a.id in $ids AND not exists { (c)<-[:HAS_SUBSIDARY]-() }
    RETURN c.id as id, c.name as name, c.summary as summary
    """
    args = request.args
    ids = args.get("ids").split(",")

    records, _, _ = driver.execute_query(query, ids=ids, _database="companies")
    results = [{"Company": r['name'], "Id": r['id'], "Summary":r['summary']} for r in records]
    return jsonify({ "output": results })


@app.route("/people_at_company", methods=["GET"])
def people_at_company():
    """
    People (name, role) associated with a company by company id
    """

    query = """
    MATCH (c:Organization)-[role]-(p:Person) WHERE c.id = $id
    RETURN replace(type(role),"HAS_","") as role, p.name as name
    """
    args = request.args
    id = args.get("id")

    records, _, _ = driver.execute_query(query, id=id, _database="companies")
    results = [{"Person": r['name'], "Role": r['role']} for r in records]
    return jsonify({ "output": results })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))