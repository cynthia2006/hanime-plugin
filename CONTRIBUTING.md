1. Clone the forked repository.
    ```sh
    $ git clone git@github.com:your-username/hanime-plugin.git
    # or,
    $ git clone https://github.com/your-username/hanime-plugin
    ```

2. Ensure [Flit](https://flit.pypa.io/en/stable/) is installed. Note that, `python3` might have to be replaced with `python`.
    ```sh
    $ python3 -m pip install flit
    $ python3 -m venv venv
    $ source venv/bin/activate
    $ flit install --only-deps
    ```

3. Export the `PYTHONPATH` variable including the current directory. This is required for **yt-dlp** to register the plugins in the `yt_dlp_plugins/extractors` directory.
    ```sh
    $ export PYTHONPATH="$PWD:$PYTHONPATH"
    ```

4. Edit the code with an editor/IDE of your choice, and check periodically with yt-dlp.
5. Stage and commit the changes, then push into your forked repository. Make sure to use [conventional commit](https://www.conventionalcommits.org/en/v1.0.0/#summary) messages.
   - For new extractors or features in existing extractors:
     ```
     feat(<site-name>): <message>
     ```
   - For bugfixes in existing extractors:
     ```
     fix(<site-name>): <message>
     ```
   - For updating (user-facing) documentation:
     ```
     docs: <message>
     ```
   - **Commits should be atomic.** 
   
     For example, if you make changes to both **hanime.tv** and **hstream.moe** extractors in your working tree, then it's better if changes are split into two separate commits such as:

     ```
     fix(hstream.moe): fixed hls extraction endpoint
     ```
     and:
     ```
     feat(hanime.tv): add support for fetching thumbnails
     ```
     instead of a single commit:
     ```
     feat: fixed hls and thumbnail grabbing
     ```

6. Create a pull request.

The development of a new plugin or fixing an existing plugin requires a degree of knowledge about the internals of yt-dlp's architecture, especially of the methods available in the `InfoExtractor` class. It is suggested to read the [official developer documentation](https://github.com/yt-dlp/yt-dlp#developing-plugins) first, then use the plugin code in this repository as a reference to obtain a general idea of problem at hand.