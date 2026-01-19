---
title: "What the applicative? Optparse-applicative from the ground up (Part 2)"
date: 2023-09-01
categories: 
  - "functional-programming"
  - "haskell"
tags: 
  - "functional-programming"
  - "haskell"
---

In this post we're going to be following on from the previous entry covering some of the foundations of how applicatives work with a slightly more concrete example. We'll be breaking down an example usage of `optparse-applicative` quite slowly to explore applicatives; if you're just looking for some examples of usage, I'd refer to the already excellent documentation [here](https://hackage.haskell.org/package/optparse-applicative).

#### Project Setup

Create a baseline project using `stack`:

```raw
$ stack new gh-cli
```

Once you've done this all we need to do is add `optparse-applicative` to our `package.yaml` file under `dependencies`:

```raw
dependencies:
- base >= 4.7 && < 5
- optparse-applicative
```

#### Setting up some working baseline code

Next let's start with a very basic example that we've shamelessly stolen from the `optparse-applicative` docs and plug this into our `Main.hs`:

```
module Main (main) where

import Options.Applicative

data Sample = Sample
  { hello      :: String
  , quiet      :: Bool
  , enthusiasm :: Int }

sample :: Parser Sample
sample = Sample
      <$> strOption
          ( long "hello"
         <> metavar "TARGET"
         <> help "Target for the greeting" )
      <*> switch
          ( long "quiet"
         <> short 'q'
         <> help "Whether to be quiet" )
      <*> option auto
          ( long "enthusiasm"
         <> help "How enthusiastically to greet"
         <> showDefault
         <> value 1
         <> metavar "INT" )
          
main :: IO ()
main = greet =<< execParser opts
  where
    opts = info (sample <**> helper)
      ( fullDesc
     <> progDesc "Print a greeting for TARGET"
     <> header "hello - a test for optparse-applicative" )

greet :: Sample -> IO ()
greet (Sample h False n) = putStrLn $ "Hello, " ++ h ++ replicate n '!'
greet _ = return ()

```

Running using stack we can see that this is working:

```raw
$ stack exec -- gh-cli-exe
Missing: --hello TARGET

Usage: gh-cli-exe --hello TARGET [-q|--quiet] [--enthusiasm INT]

  Print a greeting for TARGET

$ stack exec -- gh-cli-exe --hello Pablo
Hello, Pablo!
```

NB: I had a bit of bother getting emacs to connect to the haskell lsp having not run it in a while due to some versioning issues. For me the fix was to use ghcup to get onto all the `recommended` versions. I had to also manually point lsp-haskell to the correct path. My `init.el` file now looks like this:

```
(use-package lsp-haskell
  :ensure t
  :config
 (setq lsp-haskell-server-path "haskell-language-server-wrapper")
 ;; gives a little preview on hover, useful for inspecting types. set to nil to remove. 
 ;; full list of options here https://emacs-lsp.github.io/lsp-mode/tutorials/how-to-turn-off/
 (setq lsp-ui-sideline-show-hover t)
 (setq lsp-haskell-server-args ())
 (setq lsp-log-io t)
)
```

#### Quick refactor before we get started

In this post we're going to be breaking down exactly what's going on here; specifically looking at how applicatives are used. Before we get started let's do a quick refactor; this isn't strictly necessary but the code in the examples is a little terse so it can be harder to tell exactly what each part is doing. Right at the start of `main` we've got:

```
main = greet =<< execParser opts
  where ...
```

`=<<` is just syntactic sugar for `bind` but with the arguments reversed (ie `(a -> m b) -> m a -> m b`) which is elegant, but let's just refactor this to good old `do` notation in the interests of clarity:

```
main = do
  parsedOpts <- getInput
  greet parsedOpts
  where
    getInput = execParser opts
    opts = ...
```

Lets take this a step further and do a bit more of a tidy up, improve some variable names, add some type hints, and run `fourmolu` set the formatting:

```
data InputOptions = InputOptions
    { helloTarget :: String
    , isQuiet :: Bool
    , repeatN :: Int
    }

inputOptions :: Parser InputOptions
inputOptions =
    InputOptions
        <$> strOption
            ( long "helloTarget"
                <> metavar "TARGET"
                <> help "Target for the greeting"
            )
        <*> switch
            ( long "quiet"
                <> short 'q'
                <> help "Whether to be quiet"
            )
        <*> option
            auto
            ( long "enthusiasm"
                <> help "How enthusiastically to greet"
                <> showDefault
                <> value 1
                <> metavar "INT"
            )

main :: IO ()
main = do
    parsedInput <- getInput
    handleInput parsedInput
  where
    infoMod :: InfoMod a
    infoMod =
        fullDesc
            <> progDesc "Print a greeting for TARGET"
            <> header "hello - a test for optparse-applicative"

    parser :: Parser InputOptions
    parser = inputOptions <**> helper

    opts :: ParserInfo InputOptions
    opts = info parser infoMod

    getInput :: IO InputOptions
    getInput = execParser opts

handleInput :: InputOptions -> IO ()
handleInput (InputOptions h False n) = putStrLn $ "Hello, " ++ h ++ replicate n '!'
handleInput _ = return ()

```

We've gone a little overboard with extracting some of our variables here and we've added some redundant type declarations we don't actually need, but this hopefully helps clarify some of the types.

#### What's actually going on here?

Let's break down what's going on into chunks so we can see exactly how this works; for the sake of completeness we'll first break down our main function. The first thing we do is set up our input type `opts`:

```
    infoMod :: InfoMod a
    infoMod = fullDesc
     <> progDesc "Print a greeting for TARGET"
     <> header "hello - a test for optparse-applicative"

    parser :: Parser InputOptions
    parser = inputOptions <**> helper

    opts :: ParserInfo InputOptions
    opts = info parser infoMod
```

The key function here (`info`) is a function from optparse-applicative; it's type is

```
info :: Parser a -> InfoMod a -> ParserInfo aSource
```

All this is doing is creating a `ParserInfo` object from `Parser` (in our case of type `Parser InputOptions`) and an `InfoMod` (which in this case we're just defining inline). In our case the `Parser` is `inputOptions` and is defined above; we'll talk about this in some more detail below.

Next we're calling `execParser` (`execParser :: ParserInfo a -> IO a`) from optparse-applicative with our `ParserInfo` to tell it how to handle our input:

```
    getInput :: IO InputOptions
    getInput = execParser opts
```

Once we've got our input, we simply pass this onto our handler function and we're good to go:

```
main = do
  parsedInput <- getInput
  handleInput parsedInput
  where 
    -- etc etc
```

#### How do applicatives come into this?

The optparse-applicative library — unsurprisingly —makes use of applicative-style quite widely; let's use our instance of `inputOptions` as a specific example. For reference, the definition is here:

```
inputOptions :: Parser InputOptions
inputOptions = InputOptions
      <$> strOption
          ( long "helloTarget"
         <> metavar "TARGET"
         <> help "Target for the greeting" )
      <*> switch
          ( long "quiet"
         <> short 'q'
         <> help "Whether to be quiet" )
      <*> option auto
          ( long "enthusiasm"
         <> help "How enthusiastically to greet"
         <> showDefault
         <> value 1
         <> metavar "INT" )
```

If we remember from our last post, `<$>` is just an infix `fmap` operation; for the purposes of illustration we can start off by turning this:

```
InputOptions
      <$> strOption
          ( long "helloTarget"
         <> metavar "TARGET"
         <> help "Target for the greeting" )
```

into something thats maybe a bit more declarative like this:

```
partialInput :: Parser (Bool -> Int -> InputOptions)
partialInput = fmap InputOptions $ strOption $ long "helloTarget" <> metavar "TARGET" <> help "Target for the greeting" 

```

Here, we've pulled out the first part of our `Parser`, that so far just "wraps" a function with the remaining parameters for our `InputOptions` object. If we remember from our last post, the signature for `<*>` is

`(<*>) :: Applicative f => f (a -> b) -> f a -> f b`)

The important thing to remember here is that the function in our Parser, of type `Bool -> Int -> InputOptions`, can be thought of as having type `a -> b -> c` _or_ `a -> b` where `b` is simply a function of type `b -> c`. This allows us to use `<*>` to compose in our `Bool` parameter using `switch` and our `Int` parameter using `option auto` respectively (NB: ). In these cases `<*>` will effectively "unwrap" our `Bool`, and `Int` parameters (remember `switch` returns a `Parser Bool` and `option auto` is in our case returning a `Parser Int`) for us to build up our `InputOptions` and leave us with a `Parser InputOptions` when we're done. If we wanted to do this in the classic monadic style we'd need to do something like this:

```
withoutApp :: Parser InputOptions
withoutApp = do
  helloTarget <- strOption $ long "helloTarget" <> metavar "TARGET" <> help "Target for the greeting"
  booleanParam <- switch
          ( long "quiet"
         <> short 'q'
         <> help "Whether to be quiet" )
  intParam <- option auto
          ( long "enthusiasm"
         <> help "How enthusiastically to greet"
         <> showDefault
         <> value 1
         <> metavar "INT" )
  SomeParserConstructorThatDoesntExist $ InputOptions helloTarget booleanParam intParam

```

This is not only much less readable but also there is no public constructor for `Parser` so wouldn't work even if we wanted it to.

If you're not used to reading applicative-style code, I think it can be a little confusing to work out how the composition fits together however once the penny drops it's actually a very readable pattern. I have a suspicion this post will prove to be more of an exercise in rubber-ducking and the actual writing of it more useful than anything else, but hopefully the breakdown is a helpful illustration of how applicatives can be used in a more real-world scenario.
