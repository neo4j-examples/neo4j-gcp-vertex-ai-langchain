# Vertex AI Agent SDK Example - Company News Agent Application

## Overview

Vertex AI Agent SDK is a platform for creating and managing GenAI applications with Agents, that can use function and extension based tools to connect large language models to external systems via APIs. 

These external systems can provide LLMs with real-time data and perform data processing actions on their behalf. You can use pre-built (e.g. code-interpreter) or your own extensions in Vertex AI Agents SDK.

<!-- Learn more about [Vertex AI Extensions](https://cloud.google.com/vertex-ai/generative-ai/docs/extensions/overview).-->


### Objective

In this example, you learn how to create an extension service backend on Cloud Run, register the extension with Vertex AI Agent SDK, and then use the Agent Application in a user session.

You can answer of complex questions that combine LLM language skills with the data from the extension, allowing for multiple chained retrievals driven by the LLM.

The steps performed include:

- The Neo4j Company News database
- Creating the extension service running on Cloud Run
- Creating an OpenAPI 3.1 YAML file for the Cloud Run service
- Creating an Vertex AI Agent SDK application
- Registering the service as an extension for an agent with Vertex AI Agent SDK
- Using a session to respond to user complex user queries which will use a number of agent calls behind the scenes


## How it works 

This notebook provides an external Neo4j Extension to be used with the Agent of our application.

The extension makes a number of REST endpoints available for the agent to query a company news graph with articles about companies their industries and executives involved with the companies.

It is deployed as a Flask app in a Docker container with Google Cloud run.

This guide assumes that you are somewhat familiar with 

* [Vertex AI Agent SDK](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-api)
* [LangChain](https://python.langchain.com/docs/get_started/introduction)
* [OpenAPI specification](https://swagger.io/specification/) 
* [Cloud Run](https://cloud.google.com/run/docs)

**_NOTE_**: The notebook has been tested in the following environment:

* Python version = 3.11


## Neo4j Company News Extension 

This is the Flask application, connecting to Neo4j and hosting 6 different endpoints to retrieve information about companies, article, people, industries etc.

### Endpoints

Each endpoint takes parameters via query string and returns it's response as JSON

* `/industries` - List of Industry names
* `/companies` - List of Companies (id, name, summary) by fulltext `search`
* `/companies_in_industry` - Companies (id, name, summary) in a given industry by `industry`
* `/articles_in_month` - List of Articles (id, author, title, date, sentiment) in a month timeframe from the given `date` (yyyy-mm-dd)
* `/article` - Single Article details (id, author, title, date, sentiment, site, summary, content) by article `id`
*  `/companies_in_articles` - Companies (id, name, summary) mentioned in articles by list of article `ids`
* `/people_at_company` - People (name, role) associated with a company by company `id`

It uses a publicly hosted dataset with read-only credentials for the "companies" graph.


## Company News Service Implementation

### Connection Details

```shell
NEO4J_URI='neo4j+s://demo.neo4jlabs.com'
NEO4J_USERNAME='companies'
NEO4J_PASSWORD='companies'
NEO4J_DATABASE='companies'
```

### Endpoints and Cypher Queries


- get list of industries

```cypher
MATCH (i:IndustryCategory) RETURN i.name as industry
```

- get list of companies by fulltext search

```cypher
CALL db.index.fulltext.queryNodes('entity', $search, {limit: 100}) 
YIELD node as c, score WHERE c:Organization 
AND not exists { (c)<-[:HAS_SUBSIDARY]-() }
RETURN c.id, c.name, c.summary
```

- get list of companies in an industry

```cypher
MATCH (:IndustryCategory {name:$name})<-[:HAS_CATEGORY]-(c) 
WHERE not exists { (c)<-[:HAS_SUBSIDARY]-() }
RETURN c.id, c.name, c.summary
```

- get list of articles titles in a time frame

```cypher
match (a:Article)
where date($start) <= date(a.date)  < date($end)
return a.id, a.author, a.title, a.date, a.sentiment
```

- get article content and details

```cypher
match (a:Article)
where date($start) <= date(a.date)  < date($end)
return a.id, a.author, a.title, a.date, a.sentiment
```

- get list of companies mentioned in a list of articles

```cypher
match (a:Article)-[:MENTIONS]->(c)
where a.title in $titles
RETURN c.id, c.name, c.summary
```

- get people associated with an company

```cypher
MATCH (c:Organization)-[role]-(p:Person) WHERE c.name IN $names
RETURN c.id, c.name as company, type(role), p.name
```

### Implementation

* Flask Application
* Requirements
* Dockerfile
* Deployment to Cloud Run using gcloud CLI

### Questions:

* Who is working for more than 3 different companies in the "xxx" industry?
* Summarize articles about company X in October 2019.
* Which company in industry x had most positive sentiment in articles in Sept 2011.
