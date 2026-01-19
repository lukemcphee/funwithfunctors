---
layout: default
title: Fun with Functors
---

# Fun with Functors

Thoughts on programming, Scala, Spark, and functional ideas.

## Posts

{% for post in site.posts %}
- **{{ post.date | date: "%Y-%m-%d" }}** —
  [{{ post.title }}]({{ post.url | relative_url }})
{% endfor %}
