---
title: "What the applicative? Optparse-applicative from the ground up (Part 1)"
date: 2023-05-15
categories: 
  - "functional-programming"
  - "haskell"
tags: 
  - "functional-programming"
  - "haskell"
---

Functors and monads are both (relatively) well understood topics these days, even if they're not always labeled as these directly. Functors are everywhere, and many of the basic structures that imperative programmers use on a day-to-day basis form mondad's and can be composed accordingly. As such, once the penny drops on what a monad actually is, it's trivial to understand their application and widespread importance. Additionally, many languages have support specifically for this style of programming, making the leap very natural. Applicative functors on the other hand, are _not_ widely used by Johnny-Java-Developer and because of this there's a temptation to view them as little less intuitive and it's harder see their applications immediately. In reality applicatives are certainly no more complex than many functional concepts and can be used to facilitate some really nice patterns.

In this short series, I'm going to cover the basics of what applicatives are, and go over an example in a little more detail to show them in action (using the haskell's `optparse-applicative` library).

### What are applicative functors?

As with many functional concepts, applicative functors are fairly simple to describe; the definition for applicatives looks something like:

```raw
class (Functor f) => Applicative f where
    pure  :: a -> f a
    (<*>) :: f (a -> b) -> f a -> f b
```

For reference the standard functor is below:

```raw
class Functor f where
    fmap :: (a -> b) -> f a -> f b

-- note, we'll mainly be using the infix operator <$> in this article, described here:
(<$>) :: Functor f => (a -> b) -> f a -> f b
(<$>) = fmap
```

The first change in the applicative functor is the `pure` function, we're not going to go into this in too much detail here, for the time being just consider this as a "wrapper" function — think `Just` in `Maybe`.

The second function in applicative is more interesting: `<*>` (pronounced "app"). From the signature we can see that it's a function, that takes a function (of type `a->b`) wrapped in a functor, and a functor of type `a`, then returns a functor of type `b` — the only real difference from the standard `fmap` being that the initial function we're passing in is wrapped in a functor of the same kind. At this point, if you come from an imperative background it's tempting of thinking of a use-case that looks something like this:

```haskell
someFunc :: Num a => a -> a
someFunc = \x -> x + 1

someMaybe = Just 1

result = someFunc <$> someMaybe

-- result == Just 2
```

Which we could write using the applicative functions as:

```haskell
someFunc :: Num a => a -> a
someFunc = \x -> x + 1

someMaybe = Just 1

result = Just someFunc <*> someMaybe

result == Just 2
```

Personally, I struggled to see the point of this at first. In many languages it's simply unlikely that you'd often write something like this — if we're concerned about `someMaybe` being `Nothing`, we can still just pass in `someFunc` to `fma`p and this is handled just fine.

In all likelihood, if we had more parameters in `someFunc` we'd probably compose this monadically:

```haskell
someFunc::(Num a ) =>a -> a -> -> a
someFunc a b c = a + b + c

someResult::Maybe Int
someResult = do
  a <- Just 1
  b <- Just 2
  c <- Just 3
  Just $ someFunc a b c

```

Again this feels very familiar. The power of applicatives however really shines through though once you're working in a language with first class support for _partial application._

Let's take a really simple data class

```haskell
type Name = String
type Age = Int
type StreetName = String
type PostCode = String

data SimplePerson = SimplePerson {firstName:: Name} deriving (Show)

-- which we can create as 
sampleSimplePerson = SimplePerson "Harry"
```

Like all constructors `SimplePerson` is just a function, which in this case consumes a `Name` and returns a `SimplePerson`. If we have some function that generates a `Maybe` `firstName` for us, we can use our old friend `fmap` to generate a `Maybe SimplePerson`:

```haskell
ghci> :t SimplePerson
SimplePerson :: String -> SimplePerson

ghci> fmap SimplePerson fetchName
Just (SimplePerson {firstName = "Harry"})
```

So far so good, but let's take a type with a little more information, say:

```haskell
data Person = Person
    { name :: Name
    , age :: Age
    , postCode :: PostCode
    , streetName :: StreetName
    }
    deriving (Show)

```

```haskell
ghci> :t Person
Person :: Name -> Age -> PostCode -> StreetName -> Person
```

we can see that `fmap` isn't going to cut it — it doesn't take enough parameters. To allow us to use the same `fmap` style we used above for `SimplePerson` we'd really need something like:

```haskell
magicMap:: (Name -> Age -> PostCode -> StreetName -> Person) -> Maybe Name -> Maybe Age -> Maybe PostCode -> Maybe StreetName -> Maybe Person

```

For obvious reasons this isn't going to work for us on a practical, what we really need is a _generalised_ way of applying this kind of mapping — enter `<*>`. The critical thing to note is that working with a language like Haskell, we get partial application out the box, so if we don't apply all the parameters required to a function that's ok, we'll just get back another function that consumes the rest. That means we can write this:

```haskell
ghci> :t Person "Harry"
Person :: Age -> PostCode -> StreetName -> Person
```

Or like this:

```haskell
ghci> :t fmap Person $ Just "Harry"
fmap Person $ Just "Harry"
  :: Maybe (Age -> PostCode -> StreetName -> Person)
```

Now we're getting somewhere: what we've ended up with is a function wrapped in some context (a `Maybe`) that takes some parameters and returns our completed `Person`. In turn, this function could be called with any number of the remaining parameters, and we'll slowly work towards the end `Person`. If we stub out some extra functions to generate our required parameters wrapped in the same context we could use these to build our example outputs:

```
fetchName :: Maybe Name
fetchName = Just "Harry"

fetchAge :: Maybe Age
fetchAge = Just 21

fetchPostCode :: Maybe PostCode
fetchPostCode = Just "SUR1"

fetchStreetName :: Maybe StreetName
fetchStreetName = Just "Privet Lane"

```

Obviously we could put these together monadically:

```
personUsingDoNotation :: Maybe Person
personUsingDoNotation = do
    name <- fetchName
    age <- fetchAge
    postCode <- fetchPostCode
    streetName <- fetchStreetName
    Just $ Person name age postCode streetName

-- or using bind

personWithoutUsingDoNotation::Maybe Person
personWithoutUsingDoNotation = fetchName >>= (\name -> fetchAge >>= (\age -> fetchPostCode >>= (\postCode -> fetchStreetName >>= (\streetName -> Just $ Person name age postCode streetName))))

```

Using do-notation feels a tad overkill here and using `bind` directly is borderline unreadable, even in this simple case. Using applicative style instead however, allows us to put these together by stringing `<$>` and `<*>` as follows:

```
personUsingApp :: Maybe Person
personUsingApp = Person <$> fetchName <*> fetchAge <*> fetchPostCode <*> fetchStreetName
```

This is much nicer, hooray! Again, if we only pass in some of the parameters, we just get back a function that we can `<*>` away to as we go

```
ghci> :t Person <$> fetchName <*> fetchAge <*> fetchPostCode -- ie were missing `<*> fetchStreetName`
Person <$> fetchName <*> fetchAge <*> fetchPostCode
  :: Maybe (StreetName -> Person)
```

In the next section of this we'll be taking a look at Haskells `optparse-applicative` library, which makes extensive use of applicative style to build command line tools.
