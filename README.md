# SmartBlock

#### Video Demo: https://youtu.be/dHd6LUxP-sQ

## Description and Design Choices

SmartBlock is a system that enables the residents of our residential block 
in downtown Almaty, Kazakhstan open the vehicle barriers in our courtyard 
using their phones on mobile data, conveniently from anywhere they are, 
whereas before, opening them was only possible using RF remotes while 
being in the vicinity of the actual vehicle barrier.

I had this idea and decided to go with it for two main reasons.

Firstly, the final project assignment asked that the resulting program
should solve a real-life problem using computer code and should be
beneficial to a community or otherwise to the world, which SmartBlock
objectively does and is.

As I mentioned, before SmartBlock, the residents of our block could only
let vehicles into the courtyard using a physical RF remote, which bears
some associated issues:

-   Not everyone actually has a remote;

-   The mechanism of obtaining one if you haven't inherited it somehow
    from previous apartment owners or lost it is obscure and not
    straightforward;

-   Even if you have a remote, there are 3 apartment buildings in the
    courtyard, and naturally a lot of apartments' windows are not
    located close enough to the barrier to open it from home;

What these issues actually mean in real life is that if a person is
expecting friends, a large and heavy delivery, a repair crew or, more
importantly, an ambulance, they either have to get dressed and go
outside to open the gate even if it's subzero cold and snow ridden
outside or they have no way to open the barrier at all and are forced to
wait until someone else drives in or out and opens the barrier for them,
which might not exactly be soon for an ambulance that has arrived at
03:30 AM.

With SmartBlock however, the people can now just open the barrier as
they are on a phone call with the person calling to tell them that they
are waiting at the gate in just a couple of taps on their phone
regardless of time, distance or weather, and it works reliably every
time.

Secondly, technically, after having completed Week 9's Finance, I
suddenly had the realization that this software to open the neighborhood
gates could very much be based on the same kind of structure like
Finance:

-   a flask web application;

-   an sqlite database for users, their accounts, basic info and
    administration;

-   an html and css frontend website with what I initially saw in my
    mind as a "big red button page" + some administrative pages required
    to manage the program, so to create, delete, disable users, change
    passwords, etc.;

-   a mechanism of storing vehicle barrier operation history to have a
    log of which user did what and when;

-   A session mechanism that allows only logged-in users to have access
    to the program and to operating the hardware;

So, basically, the program could borrow a whole lot from the Finance web
app I had just built as Week 9 homework. Plus, with CS50 being my only
exposure to the world of programming, this was also the only thing I had
learned, so using it as a framework made a lot of sense. I realized that
all I had to do was figure out how to build the element of actual
barrier operation into it and that would be it.

## How SmartBlock Works

SmartBlock is a Flask web application that runs on a raspberry pi
minicomputer located inside the barrier terminal. The raspberry pi is
itself the server and users reach the application via a Cloudflare
tunnel setup which is an idea that came about from consulting Chat GPT
on how to implement the application to, importantly, make it free of
charge for the users.

Another technical feature of the app, that also helps keep it free of
charge, is that it uses my home Wi-Fi network for its connection to the
internet. My window isn't located near the barrier terminal; however,
this was resolved by employing a 2-piece Wi-Fi bridge with the emitting
element attached to my balcony and the receiving one installed inside
the barrier terminal neatly behind a ventilation opening with a plastic
grille for good signal reception.

The pi is connected via pins to a relay which is pinned into the
barrier's control board to energize for 1.5 seconds and open the gate 
when an open request is received by the backend.

Use of the program is optional, so the people who don't wish to use it
can just continue using their RF remotes. There is no interference with
the remotes' operation from SmartBlock.

The software process is as follows:

-   the user is onboarded manually as this gives access to hardware and
    an actual courtyard for vehicles;

-   the user logs in with an account stored in the sqlite database; a
    flask session keeps them authenticated;

-   on the main page, the user taps a big button that needs to be held
    for 1 second to open so as to avoid accidental taps;

-   after the 1 s hold is complete, the browser sends a request to the
    /open route in app.py which verifies that the user's account is
    active and checks the 5 second hardware cooldown period; Chat GPT
    helped implement the hold button feature;

-   there is a 5-second cooldown in the backend so that users, including
    multiple users, could not overrun the relay with simultaneous
    requests putting the physical hardware at risk;

-   flask calls open_barrier() in hardware.py; this activates GPIO pin
    17 on the raspberry pi, energizing the relay and operating the
    barrier;

-   after the command is successfully sent, the application inserts an
    entry on the operation into the history table associated with the
    user's ID.

## User Features

Users can log in, log out, change their password, view their action
history and, most importantly, operate the barrier from their phone.

## Administrator Features

-   the administrator creates an account for users, sends them their
    username and a temporary password that they have to change to their
    own in order to toggle a must_change_password boolean value to
    actually start using the app;

-   the administrator can view everyone's action history and not just
    their own

-   the administrator can disable and delete users; the delete is a soft
    delete, so users' information continues to be stored in order to not
    mess up the action history;

## Project Files

Following closely the learned CS50 Finance philosophy, the project
features the following files:

An app.py which serves as the main backend of the application. It has
different routes that use either the /get or /post method to do things
and render pages. It creates and configures the flask app, connects to
the sqlite database, manages sessions and contains all the different
routes needed for all the hardware operation and administrative
functions. It uses a simple is_admin Boolean flag to differentiate
between the admin and regular users.

This is also where the hardware cooldown lives to make sure it's not
browser or user dependent and works reliably as a single source of
truth. The cooldown uses the concept of a monotonic clock, which is also
something Chat GPT helped with. It was important the cooldown be 100%
reliable to not damage the community hardware.

Hardware.py is a small file that is responsible for the relay operation
logic that was hard-won by testing in the field. The simple logic used
here turned out to be the best. The current logic creates the
OutputDevice anew at every press of the button by saying barrier_relay =
OutputDevice(...). The very first version created OutputDevice for the
entire lifetime of the app thus holding the pin for the duration of the
app's service and, as it turned out, locking out all the residents' RF
remotes and making them unable to open the barrier (Yikes!).

Helpers.py which is almost copied off Finance to implement the
login_required() and apology() functions.

smartblock.db -- the sqlite3 database with two tables: users and events
for all user related info and opening history.

The templates folder with all the html pages for the different routes.
The html pages use jinja and extend layout.html for convenience and
efficiency following the Finance approach.

A styles.css for the visual styling and mobile screen rules just like in
Finance.

A requirements.txt for all the packages and libraries that the
application depends on.

.gitignore to specify the files and directories that should remain local
and should not be uploaded to Git, including the virtual environment,
secret key and the database. Chat GPT helped me somewhat more heavily
here with gitignore and .venv virtual environment, etc. as these were
concepts that I wasn't quite familiar with before.

## Deployment

The application is deployed right on the raspberry pi installed inside
the barrier terminal and not on a conventional web server. I do
understand the security implications of this, however:

-   it was important that the application be completely free of charge
    for the residents;

-   I am not storing any actual personal information in the database;

-   the design basis threat, so to speak, for this case is very
    non-plausible, so all in all, for this practice application I
    believe this solution to be quite OK.

I used Gunicorn (guided by Chat GPT) as the application server instead
of Flask's development server.

I used systemd (also guided by Chat GPT) so that the app runs as a
cs50-smartblock.service allowing the app to be started or stopped as a
Linux service.

I bought the domain smartblock.kz online and used a Cloudflare tunnel
(recommended and largely guided by Chat GPT) to make the application
accessible without having a static IP address and to serve the public
domain address cs50.smartblock.kz which the residents use to place
requests which are then forwarded to the application that is running
locally on port 5001.

The app installs cleanly by hitting Share -- Add to Home Screen and
launches as an actual phone app making it convenient for the residents
while maintaining the 100% free of charge philosophy.

## What I Learned

I learned a lot from this final project assignment and the CS50 course
itself as a whole.

I started as a conference interpreter feeling AI threatened and wishing
to expand my expertise and transition to IT. I had no idea how to
approach building an app or developing any kind of software system.

Apart from learning generally how computers work, and what programming
languages are, which I still find valuable even in the rapidly evolving
AI era, I also learned the whole structure of developing an application
from scratch, and I actually physically did it myself, and now there is
an application running on my block that is used on a daily basis by 30+
people in my local community for their convenience.

In my mind, computer programs changed from being magic to being a
specific structure.

I started the course back in late November of last year. The exponential
development of AI has made strides since then, right as I was tinkering
at home with my course homework, and right at the same time as I was
taking the course, this whole hype unfolded with AI taking jobs and
employment opportunities from junior and starting software engineers.
And here I was suffering through learning how to code basic functions 
in C.

On a side note, after completing the initial CS50 version of SmartBlock,
I also taught myself the agentic coding workflow with Claude Code and
used it to develop a much more extensive "enterprise" version of
SmartBlock. It supports multiple barriers and includes features such as
guest access links, diagnostics and even siren recognition-based
automatic emergency-vehicle detection. That extended version is now the
one actually running on our courtyard barriers. However, it grew
directly out of this CS50 project; without CS50 I probably would never
have become interested enough in programming to attempt something like
it.

So now with the onslaught of AI on people's professional careers, it is
for now uncertain what I'm going to do with this newly acquired
knowledge, but I do plan to keep studying further in the field of IT to
eventually, possibly, pursue a position that cannot be fully replaced by
AI.
