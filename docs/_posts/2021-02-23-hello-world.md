---
title: "Quickstart with Zeppelin, Scala, Spark & Docker"
date: 2021-02-23
categories: 
  - "docker"
  - "scala"
  - "spark"
  - "zeppelin"
tags: 
  - "docker"
  - "scala"
  - "spark"
  - "zeppelin"
---

Recently, I've been working on a problem that required doing some exploratory analysis on some of our more high throughput datasources. Where we've had to do this kind of work in the past the approach has typically been to reach for the usual suspects; python and pandas, probably running in jupyter notebooks. Whilst I've written quite a bit of python over the years and will occasionally reach for it to whip up a script for this or that, I find the lack of type safety for anything more involved than bashing together a script to automate something simple really frustrating, so I decided to try out Apache Spark using Scala. After a quick trial of running some code in both Apache Zeppelin and Jupyter using the spylon-kernal, Zeppelin quickly emerged victorious (in my mind) and so far has been an absolute joy to work with.

The purpose of this post is not to provide yet another x vs y technology breakdown (there's plenty of those on the topic already), but rather to private a brief intro on how to get up and running quickly with a Zeppelin/ Spark/ Scala stack.

#### Installation

For a full local installation of zeppelin the official docs recommend that you download the binaries and run these against a (local or otherwise) spark installation, however for trialing out the stack and for situations where you don't need a full scale cluster, it's docker to the rescue.

Let's create our docker-compose.yml:

```shell
$ mkdir zeppelin && cd $_ && touch docker-compose.yml
```

In this we want to insert the following:

```yaml
version: "3.3"
services:
  zeppelin:
    image: apache/zeppelin:0.9.0
    environment:
      - ZEPPELIN_LOG_DIR=/logs
      - ZEPPELIN_NOTEBOOK_DIR=/notebook
    ports:
      - 8080:8080
    volumes: # to persist our data once we've destroyed our containers
      - ./notebook:/notebook 
      - ./logs:/logs
```

Now all we need to do now is start up our container:

```shell
$ docker-compose up
```

Wait a minute to let docker start up our container, then navigate to 127.0.0.1:8080 and you should see that Zeppelin has started up:

![]({{ "/assets/images/image-1024x454.png" | relative_url }})

##### Speaking to spark

The first thing we'll want to do is set up a SparkSession, which we're going to be using as our main entry point; by default zeppelin injects a SparkContext into our environment in a variable named `sc`, from which we can create our session.

```scala
import org.apache.spark.sql.SparkSession
val spark = SparkSession.builder.config(sc.getConf).getOrCreate()
```

![]({{ "/assets/images/image-2-1024x75.png" | relative_url }})

From here let's start doing something more useful. Rather than going through yet another exercise in map-reduce-to-count-word-frequencies-in-a-string, let's pop across to the https://ourworldindata.org GitHub repo, and grab some sample data; there's lots of data on the current COVID pandemic, so let's use this. I'll include the actual files used in the GitHub repo for this, but the following link should get you the most up to date data at their repo [here](https://github.com/owid/covid-19-data/blob/master/public/data/vaccinations/vaccinations.csv).

Spark has multiple API's we can use to interact with our data, namely Resilient Distributed Datasets (RDD's), Dataframes and Datasets. Dataframes and Datasets were introduced as of Spark 2.0, and will be the API's we're using here. To load our csv data and see our new schema we simply need to call:

```scala
val df = spark.read
         .format("csv")
         .option("header", "true") // first line in file is our headers
         .option("mode", "DROPMALFORMED")
         .option("inferSchema", "true") // automatically infers the underlying types, super helpful
         .load("/notebook/vaccinations.csv")

df.printSchema
```

![]({{ "/assets/images/image-4.png" | relative_url }})

Let's start with something really simple, and look to see which country as issued the most vaccinations so far:

```scala
val totalVaccinations = df
    .groupBy("location")
    .sum("daily_vaccinations")
    .sort(desc("sum(daily_vaccinations)")) 

// alternatively if we want to use named fields we could also do something like this
df.groupBy("location")
    .agg(sum("daily_vaccinations") as "vaccinationsSum")
    .sort(desc("vaccinationsSum")) 

totalVaccinations.show(10)
```

![]({{ "/assets/images/image-6.png" | relative_url }})

This gives us a high level picture of the sum of our efforts, but say we want to find out how this has developed over time, we might start by collecting the total vaccinations together and sorting them by date so we can track how this changes; something like this:

```scala
val vaccinations = df.select("location", "date", "total_vaccinations")
        .withColumn("date", to_date(col("date"),"yyyy-MM-dd")) // convert our dates into a more usable format
        .sort("date")
        .sort("location")
```scala
vaccinations.createOrReplaceTempView("vaccinations") // we'll use this later
```

This is obviously rather a lot of data so we can filter this slightly to try to see what's going on:

```scala
vaccinations
    .filter(col("location") === "United States" ||  col("location") === "United Kingdom").sort("location", "date")
    .show(100)
```

```raw
+--------------+----------+------------------+
|      location|      date|total_vaccinations|
+--------------+----------+------------------+
|United Kingdom|2020-12-20|            669674|
|United Kingdom|2020-12-21|              null|
|United Kingdom|2020-12-22|              null|
|United Kingdom|2020-12-23|              null|
|United Kingdom|2020-12-24|              null|
|United Kingdom|2020-12-25|              null|
|United Kingdom|2020-12-26|              null|
|United Kingdom|2020-12-27|            996616|
|United Kingdom|2020-12-28|              null|
|United Kingdom|2020-12-29|              null|
|United Kingdom|2020-12-30|              null|
|United Kingdom|2020-12-31|              null|
|United Kingdom|2021-01-01|              null|
|United Kingdom|2021-01-02|              null|
|United Kingdom|2021-01-03|           1389655|
|United Kingdom|2021-01-04|              null|
|United Kingdom|2021-01-05|              null|
|United Kingdom|2021-01-06|              null|
|United Kingdom|2021-01-07|              null|
|United Kingdom|2021-01-08|              null|
|United Kingdom|2021-01-09|              null|
|United Kingdom|2021-01-10|           2677971|
|United Kingdom|2021-01-11|           2843815|
|United Kingdom|2021-01-12|           3067541|
|United Kingdom|2021-01-13|           3356229|
|United Kingdom|2021-01-14|           3678180|
|United Kingdom|2021-01-15|           4006440|
|United Kingdom|2021-01-16|           4286830|
|United Kingdom|2021-01-17|           4514802|
|United Kingdom|2021-01-18|           4723443|
|United Kingdom|2021-01-19|           5070365|
|United Kingdom|2021-01-20|           5437284|
|United Kingdom|2021-01-21|           5849899|
|United Kingdom|2021-01-22|           6329968|
|United Kingdom|2021-01-23|           6822981|
|United Kingdom|2021-01-24|           7044048|
|United Kingdom|2021-01-25|           7325773|
|United Kingdom|2021-01-26|           7638543|
|United Kingdom|2021-01-27|           7953250|
|United Kingdom|2021-01-28|           8369438|
|United Kingdom|2021-01-29|           8859372|
|United Kingdom|2021-01-30|           9468382|
|United Kingdom|2021-01-31|           9790576|
|United Kingdom|2021-02-01|          10143511|
| United States|2020-12-20|            556208|
| United States|2020-12-21|            614117|
| United States|2020-12-22|              null|
| United States|2020-12-23|           1008025|
| United States|2020-12-24|              null|
| United States|2020-12-25|              null|
| United States|2020-12-26|           1944585|
| United States|2020-12-27|              null|
| United States|2020-12-28|           2127143|
| United States|2020-12-29|              null|
| United States|2020-12-30|           2794588|
| United States|2020-12-31|              null|
| United States|2021-01-01|              null|
| United States|2021-01-02|           4225756|
| United States|2021-01-03|              null|
| United States|2021-01-04|           4563260|
| United States|2021-01-05|           4836469|
| United States|2021-01-06|           5306797|
| United States|2021-01-07|           5919418|
| United States|2021-01-08|           6688231|
| United States|2021-01-09|              null|
| United States|2021-01-10|              null|
| United States|2021-01-11|           8987322|
| United States|2021-01-12|           9327138|
| United States|2021-01-13|          10278462|
| United States|2021-01-14|          11148991|
| United States|2021-01-15|          12279180|
| United States|2021-01-16|              null|
| United States|2021-01-17|              null|
| United States|2021-01-18|              null|
| United States|2021-01-19|          15707588|
| United States|2021-01-20|          16525281|
| United States|2021-01-21|          17546374|
| United States|2021-01-22|          19107959|
| United States|2021-01-23|          20537990|
| United States|2021-01-24|          21848655|
| United States|2021-01-25|          22734243|
| United States|2021-01-26|          23540994|
| United States|2021-01-27|          24652634|
| United States|2021-01-28|          26193682|
| United States|2021-01-29|          27884661|
| United States|2021-01-30|          29577902|
| United States|2021-01-31|          31123299|
| United States|2021-02-01|          32222402|
| United States|2021-02-02|          32780860|
+--------------+----------+------------------+
```

Still, this is hardly ideal and leads us nicely into the fantastic data visualisation support that zeppelin gives us. In the block where we generated our dataframe containing the total vaccinations by data and country earlier, you'll see we also created a view using the `createOrReplaceTempView` function; this creates a view against which we can run good old fashioned sql to query and visualise our data. Simply add in `%spark.sql` in at the top of your block and you're good to go:

```sql
%spark.sql
/* note that we need to order by date here 
 even though we've already sorted our data frame, if we don't to this 
 zeppelin will group dates where we have values for each element in the group together 
 and our graphs will come out with the order messed up */
select location, date, total_vaccinations from vaccinations order by date
```

Note that you'll need to click into settings and select which fields we're going to be using and for what:

![]({{ "/assets/images/image-8-1024x318.png" | relative_url }})

![]({{ "/assets/images/image-7-1024x309.png" | relative_url }})

Whist this output is naturally very busy, and a little overwhelming on my 13" MacBook, we're immediately getting a decent view into our data. Picking a few countries at random we can slim this down to allow us to compare whomever we wish:

```scala
val filterList = Seq("United States", "United Kingdom", "France")
val filtered = vaccinations
                    .filter(col("location").isin(filterList : _*))
                    .sort("location", "date")
filtered.createOrReplaceTempView("filtered")
```

```sql
%spark.sql
select * from filtered sort by date
```

![]({{ "/assets/images/image-9-1024x245.png" | relative_url }})

Easy!

One final thing I'd like to touch on. So far we've been dealing only with Spark Dataframes, the weakly typed cousin of the Dataset. Whilst I surprisingly really like the stringly-typed nature of the Dataframe, particularly for the speed at which it allows us to play around with the data, for anything other than exploratory analysis or small scale projects this is obviously inadequate. Fortunately Spark adding this information in is trivial. All we need to do is define the shape of our object, and pass this into `as` as our type parameter.

```scala
import sqlContext.implicits._ // import so we can use $ rather than col("some_col")

// note we're defining peopleVaccinated as an Optional here, preventing any nasty surprises
case class Details(
    location: String, 
    isoCode:String, 
    peopleVaccinated: Option[Int], 
    date: java.sql.Timestamp
)

val detailsDs = df.select(
        $"location", 
        $"iso_code" as "isoCode", 
        $"people_vaccinated" as "peopleVaccinated",
        $"date")
    .as[Details]

```scala
val ukResults = detailsDs.filter(details => details.location.equals("United Kingdom"))
```

Additionally, if we supply type information and use Dataset's, Zeppelin provides us with some autocomplete functionality.

![]({{ "/assets/images/image-11.png" | relative_url }})

Whilst this support does move us in the right direction, it is a bit sluggish to be honest and isn't really a substitute for a real IDE.

#### Conclusion

So far I've had a pretty good experience with Zeppelin and I really like what it's got to offer; the tooling does exactly what I want from it and by running in docker it's easy to get an environment spun up in a minutes. Whilst the out-of-the-box experience isn't up to par with a proper IDE, if you've got an IntelliJ Ultimate licence, the integration with Big Data Tools brings this in line. Even for simple data analysis, comparing to tools like python/ pandas, the Scala/Spark/Zeppelin stack is a great choice for most use-cases, where we'd typically end up using a python/pandas stack.
