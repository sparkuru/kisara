# Local Docker builds

## NapCat

`napcat/repo` is a local checkout of the XingYunStar NapCatQQ archive. It is
ignored by the parent repository; its Git history and source are kept separately.
The Docker build copies that checkout into a Node build stage and builds the
WebUI and NapCat Shell. It does not clone or pull the source in the container.

The resulting `kisara/napcat:local` image replaces the Shell archive in an
existing local NapCat/QQ runtime image. The runtime layer supplies Linux QQ,
system libraries and the original container entrypoint; this is not a complete
build of Linux QQ from source. Preserve that runtime image or an image archive
if it needs to be rebuilt on another machine. The default runtime image is
`mlikiowa/napcat-docker:latest`; `NAPCAT_RUNTIME_IMAGE` selects a different
compatible local image. The default build image is `node:22.22.0-bookworm`;
`NAPCAT_BUILDER_IMAGE` selects another compatible local Node image.

Both images must already be present locally. The build script does not pull
images. Installing pnpm and JavaScript dependencies during the build requires
network access to package registries and native build dependencies such as
Node.js headers.

The [XingYunStar v4.18.42 release](https://github.com/XingYunStar/NapCatQQ/releases/tag/v4.18.42)
lists runtime image archives and checksum files. An archive can be loaded with
`docker load -i <archive>`, then selected with `NAPCAT_RUNTIME_IMAGE` using
the imported tag. Its checksum verifies the downloaded file's integrity; it
does not independently establish the archive's origin.

```bash
git clone https://github.com/XingYunStar/NapCatQQ.git docker/napcat/repo
./docker/napcat/build.sh
```

Skip the clone when the checkout already exists. The script builds its current
working tree; `NAPCAT_BUILD_IMAGE` changes the output tag and
`NAPCAT_BUILD_VERSION` overrides the version inferred from Git tags. The
current checkout commit and its clean/dirty state are recorded in image labels.

The existing Compose and preview setups default to `kisara/napcat:local`.
An explicit `NAPCAT_IMAGE` in `.env` or the calling environment overrides
that default. The build itself does not start or replace running services;
recreate the NapCat container after changing its image. Test login, the OneBot
connection, and any required QQ behavior after switching.

The existing Telegram Bot API image build remains in
[`deploy/telegram-bot-api.Dockerfile`](../deploy/telegram-bot-api.Dockerfile).
