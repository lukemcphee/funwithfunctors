---
title: "Building a back-end web stack in OCaml — Postgres, Caqti V2 &amp; Opium"
date: 2023-11-01
---

There's a couple of choices when looking to build web-servers in OCaml; 2 commonly used choices seem to be postgres and [caqti](https://github.com/paurkedal/ocaml-caqti) for the database layer, and [dream](https://github.com/aantron/dream) for running the http-server. Both have half decent documentation and a couple of examples in the git repo's to work off, however caqti recently released a new major version (>2) and dream relies on an older version (<=1.9.0); some fairly hefty breaking changes in this version precludes our using the two together if we want to use the most recent versions of both. One other option for building a web-layer is [Opium](https://github.com/rgrinberg/opium); this has a very similar, fairly high-level feel to dream. The official docs for opium reference [this](https://shonfeder.gitlab.io/ocaml_webapp/) excellent blog post however again the version of caqti is pretty old; you can get the gist from here but if you'll run into issues if you try to lift and shift and use caqti >2 so i've put together this post which uses the latest version.

## Setup

First create a new project

```shell
dune init project shorty
```

Once we've got our new project, add the dependencies we're going to need into our

To install the dependencies we'll need, update your `dune-project` file so your dependencies section so it contains the following dependencies

```dune
 (depends ocaml dune
  lwt
  lwt_ppx
  core
  caqti
  caqti-lwt
  caqti-driver-postgresql
  ppx_inline_test
  ppx_deriving_yojson
  opium
)

```

To install all these run `opam install ./ --deps-only` on your base project directory. This can be run any time you want to add a dependency to this file and saves you running `opam install xyz` every time. Next, let's update our project structure a little. Rather than have a single `lib` directory, to me it makes more sense to split this up as we would in a real project.

```shell
mkdir lib/repo
mv lib/dune lib/repo
```

Our `repo` directory is going to contain everything we need for interacting with the db layer, so let's update our library name and add the dependencies we'll need:

```dune
(library
 (name repo)
 (libraries
  caqti
  caqti-driver-postgresql
  caqti-lwt.unix
  yojson
  core
  ppx_deriving_yojson.runtime)
 (preprocess
  (pps ppx_deriving_yojson)))
```

Next, let's create a postgres instance we can interact with. In our base directory add a `docker-compose.yml` file containing the following:

```yaml
version: '3'
services:
  flyway:
    image: flyway/flyway:6.3.1
    command: -configFiles=/flyway/conf/flyway.config -locations=filesystem:/flyway/sql -connectRetries=60 migrate
    volumes:
      - ${PWD}/sql_versions:/flyway/sql
      - ${PWD}/docker-flyway.config:/flyway/conf/flyway.config
    depends_on:
      - postgres
  postgres:
    image: postgres:12.2
    restart: always
    ports:
    - "5432:5432"
    environment:
    - POSTGRES_USER=example-username
    - POSTGRES_PASSWORD=pass
    - POSTGRES_DB=shorty-db

```

Note that we're using flyway for our database migrations; we're mounting a config file and our migrations directly to this image, let's create these now:

Create a file `docker-flyway.config` containing:

```properties
flyway.url=jdbc:postgresql://postgres:5432/shorty-db
flyway.user=example-username
flyway.password=pass
flyway.baselineOnMigrate=false
```

and add a simple migration to get us started to `sql_versions/V1__Create_link_table.sql`

```sql
CREATE TABLE entry (
    short_url varchar(50),
    target_url varchar(50),
    PRIMARY KEY(short_url,target_url)
);
```

I've added the following to a file named `nuke_docker_and_restart.sh` to allow us to completely tear the db down when we're done to make it easier to write tests against.

```shell
docker-compose rm -f
docker-compose pull
docker-compose up
```

Running this we can see our database coming up and flyway applying our migrations to create our table to test against.

## Database layer and caqti

Before we add our code to interact with the db, i've created a `Util.ml` file containing some helper functions:

```ocaml
let get_uri () = "postgres://example-username:pass@localhost:5432/shorty-db"

let str_error promise =
  Lwt.bind promise (fun res ->
      res |> Result.map_error Caqti_error.show |> Lwt.return)

let connect () =
  let uri = get_uri () in
  Caqti_lwt_unix.connect (Uri.of_string uri)

(** Useful for `utop` interactions interactions. See `README.md`.*)
let connect_exn () =
  let conn_promise = connect () in
  match Lwt_main.run conn_promise with
  | Error err ->
      let msg =
        Printf.sprintf "Abort! We could not get a connection. (err=%s)\n"
          (Caqti_error.show err)
      in
      failwith msg
  | Ok module_ -> module_

```

Obviously in the real world we would _not_ want to pass in our database credentials like this, but it will do for this example. You can ignore `connect_exn`, I've included examples of how to use this in the repo `README.org` if you'd like to see how to interact with the db from utop. Next we need to create our `Db.ml` file, where we'll house the bulk of our code for interacting with the db.

```ocaml
module Model = struct
  type entry = { short_url : string; target_url : string } [@@deriving yojson]
  type entry_list = entry list [@@deriving yojson]

  let entries_to_json entries = entry_list_to_yojson entries

  let tuple_to_entry tup =
    let a, b = tup in
    let entry : entry = { short_url = a; target_url = b } in
    entry

  let entry_to_json (a : entry) = entry_to_yojson a
end

module Q = struct
  open Caqti_request.Infix

  (*
    Caqti infix operators

    ->! decodes a single row
    ->? decodes zero or one row
    ->* decodes many rows
    ->. expects no row
  *)

  (* `add` takes 2 ints (as a tuple), and returns 1 int *)
  let add = Caqti_type.(t2 int int ->! int) "SELECT ? + ?"

  let insert =
    Caqti_type.(t2 string string ->. unit)
      {|
       INSERT INTO entry (short_url, target_url)
       VALUES (?, ?)
      |}

  let select =
    Caqti_type.(unit ->* t2 string string)
      {|
       SELECT short_url
            , target_url
       FROM entry 
      |}
end

let add (module Conn : Caqti_lwt.CONNECTION) a b = Conn.find Q.add (a, b)

let insert (module Conn : Caqti_lwt.CONNECTION) short_url target_url =
  Conn.exec Q.insert (short_url, target_url)

let find_all (module Conn : Caqti_lwt.CONNECTION) =
  let result_tuples = Conn.collect_list Q.select () in
  Lwt_result.bind result_tuples (fun xs ->
      let out = List.map Model.tuple_to_entry xs in
      Lwt_result.return out)

let resolve_ok_exn promise =
  match Lwt_main.run promise with
  | Error _ -> failwith "Oops, I encountered an error!"
  | Ok n -> n

```

Let's break this down a little. First up we have our `Model` module. In here we've housed a couple of basic types. Note that we've added `[@@deriving yojson]` to the back of these; this is a language extension which automatically generates functions for converting to and from json (eg `entry_to_yojson` ), thus why there's nothing manually declared with these names!

Next we've declared our `Q` module where we're adding our queries. Let's break one of our queries down to clarify exactly what's going on (I've added the return type to the declaration so it's a little clearer what we're creating):

```ocaml
  let insert: (string * string, unit, [ `Zero ]) Caqti_request.t =
    Caqti_type.(t2 string string ->. unit)
      {|
       INSERT INTO entry (short_url, target_url)
       VALUES (?, ?)
      |}
```

One thing to note: `Caqti_type.(stuff)` is an example of ocaml's "local open" syntax; effectively all this is doing is

```ocaml
let open Caqti_type in 
stuff
```

to give us access to `Caqti_type`'s scope. Within this scope we can access `[t2](https://paurkedal.github.io/ocaml-caqti/caqti/Caqti_type/index.html#val-t2)`. This function consumes some local types and returns a function

``?oneshot:bool -> string -> (string * string, unit, [ `Zero ]) Caqti_request.t``

which we then pass our sql statement into. I think it's worth calling out here the parameters we're passing to t2 and `->.` (ie `string string` & `unit`) and _not_ OCaml primitives; In this context `string` and `unit` refer to local type declarations within `Caqti_type` with specific meanings; the docs for these are [here](https://paurkedal.github.io/ocaml-caqti/caqti/Caqti_type/index.html#val-string). Apparently this is an intentional design pattern however I'll admit a wariness to this; to me it feels like it's going to create code that's more difficult to read. Our `Caqti_request.t` output is parameterised by `(string * string, unit, [ Zero ])` which gives us a nice clear description of how to use our `insert` request; it takes a tuple of two strings and returns unit. Again, it's worth noting that OCaml's syntax for type parameters is "backwards" compared to a lot of languages — eg where in something like scala we'd write `List[String]` in OCaml this would be `String List`.

In the next block we're simply writing some functions which consume connections and some parameters and proxy these through to our queries.

At this point we've got some queries which we can use to interact with the database, let's write some tests to make sure they work. Using the same directory structure as before, we'll add our tests under `lib/repo/db.ml` and add our dependencies under `lib/repo/dune`:

```dune
(library
 (name repo_test)
 (inline_tests)
 (libraries repo)
 (preprocess
  (pps ppx_inline_test ppx_assert)))
```

and

```ocaml
 open Repo.Db.Model

let str_error promise =
  Lwt.bind promise (fun res ->
      res |> Result.map_error Caqti_error.show |> Lwt.return)

let drop_id_from_entry triple = (triple.short_url, triple.target_url)

let%test_unit "PostgreSQL: add (asynchronously)" =
  let ( => ) = [%test_eq: (Base.int, Base.string) Base.Result.t] in
  let will_add a b =
    let ( let* ) = Lwt_result.bind in
    let* conn = Repo.Util.connect () |> str_error in
    Repo.Db.add conn a b |> str_error
  in
  Lwt_main.run (will_add 1 2) => Ok 3

let%test_unit "Able to add to the database" =
  let ( => ) =
    [%test_eq:
      ((Base.string * Base.string) Base.list, Base.string) Base.Result.t]
  in
  let input_url = "hello" in
  let target_url = "Arnie" in
  let add_entry =
    let ( let* ) = Lwt_result.bind in
    let* conn = Repo.Util.connect () |> str_error in
    let* _ = Repo.Db.insert conn input_url target_url |> str_error in
    Lwt_result.bind (Repo.Db.find_all conn) (fun res ->
        Lwt_result.return @@ List.map drop_id_from_entry res)
    |> str_error
  in
  Lwt_main.run add_entry => Ok [ (input_url, "Arnie") ]
```

To run these:

```shell
$ ./nuke_docker_and_restart.sh
# and in another window
$ dune runtest
```

At this point we've got everything we need up and running to interact with our little database, now we're ready to add our Opium layer. This part is fairly simple, we could add to a `lib/controllers/` repo but for the sake of simplicity we're just going to add everything to our `bin/main.ml` file and `bin/dune` the requisite dependencies.

```dune
(executable
 (public_name shorty)
 (name main)
 (libraries repo lwt opium)
 (preprocess
  (pps lwt_ppx)))
```

```ocaml
open Opium
open Repo
open Repo.Db

let convert_to_response entries =
  let as_json = Response.of_json @@ Model.entries_to_json entries in
  Lwt_result.return as_json

let find_all _ =
  Logs.info (fun m -> m "Finding all");
  let get_all =
    let ( let* ) = Lwt_result.bind in
    let* conn = Util.connect () in
    let entries = Db.find_all conn in
    Lwt_result.bind entries convert_to_response
  in
  Lwt.bind get_all (fun r ->
      match r with Ok r -> Lwt.return r | Error _ -> raise @@ Failure "")

let put_entry req =
  Logs.info (fun l -> l "adding entry");
  let insert =
    let open Lwt.Syntax in
    let+ json = Request.to_json_exn req in
    let entry = Model.entry_of_yojson json in
    (* manually declare let* as from Lwt_result as it's also available on the base Lwt *)
    let ( let* ) = Lwt_result.bind in
    let* conn = Util.connect () in
    match entry with
    | Ok e -> Db.insert conn e.short_url e.target_url
    | Error e -> raise @@ Failure e
  in
  let bind_insert insert_response =
    Lwt.bind insert_response (fun bind_response ->
        Lwt.return
        @@
        match bind_response with
        | Ok _ -> Response.of_plain_text "Hooray"
        | Error _ ->
          (* This isn't brilliant, ideally we'd handle different excpetions with specific/ sensible http code *)
            Response.of_plain_text ~status:`Bad_request
              "Oh no something went terribly wrong")
  in

  Lwt.bind insert bind_insert

let _ =
  Logs.set_reporter (Logs_fmt.reporter ());
  Logs.set_level (Some Logs.Info);
  Logs.info (fun m -> m "Starting run");
  App.empty |> App.get "/entry" find_all |> App.put "/entry" put_entry
  |> App.run_command

```

Opium has a really simple api; `App.get` and `Api.put` both have signature

```ocaml
string -> (Request.t -> Response.t Lwt.t) -> App.t -> App.t
```

where the first parameter is the route we're binding to then the handler function to call.

Spinning up our app we're now able to add and view entries in our db over our new server:

```shell
# first window 
$ dune exec -- shorty
# second window
$ ./nuke_docker_and_restart.sh
# third window
$ http PUT 127.0.0.1:3000/entry short_url=hello target_url=vinnie
HTTP/1.1 200 OK
Content-Length: 6
Content-Type: text/plain

Hooray

$ http 127.0.0.1:3000/entry
HTTP/1.1 200 OK
Content-Length: 45
Content-Type: application/json

[
    {
        "short_url": "hello",
        "target_url": "vinnie"
    }
]

# send the same value again to test our exception handling
http PUT 127.0.0.1:3000/entry short_url=hello target_url=vinnie
HTTP/1.1 400 Bad Request
Content-Length: 26
Content-Type: text/plain

Oh no something went terribly wrong

```

### Conclusion

Opium and Caqti have both proven really nice libraries to work with, albeit in this simple example. Both are extremely lightweight and easy to get up and running quickly with. I've pushed the changes up to [github](https://github.com/lukemcphee/shorty), hopefully this provides an easy-to-use sample project for anyone looking to serve up an api in OCaml.
