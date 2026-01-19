---
layout: default
title: Fun with Functors
---

# Fun with Functors

Welcome to fun with functors, my functional programming blog. 

Here I write about programming, mainly with a functional-first bias, but may cover other topics along the way.

## Posts
{% for post in site.posts %}
### {{ post.title }}
**{{ post.date | date: "%Y-%m-%d" }}**

{{ post.excerpt }}

[Read more →]({{ post.url | relative_url }})

---

{% endfor %}
