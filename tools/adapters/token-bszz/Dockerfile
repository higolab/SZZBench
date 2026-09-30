# check=skip=FromPlatformFlagConstDisallowed
# (srcML 1.0.0 exists for amd64 only, so the platform is fixed on purpose.)
#
# The toolchain that makes token-level histories for tools/adapters/token_bszz_to_predictions.py:
# the MV-SZZ replication package's docker/cregit image, rebuilt on images that are still published.
#
#   docker build --platform linux/amd64 -t szzbench-token-bszz tools/adapters/token-bszz
#
# - The replication package starts from sbtscala/scala-sbt:8-jdk-focal, which is no longer
#   published; this starts from eclipse-temurin:8-jdk-focal (JDK 8, Ubuntu 20.04) and adds sbt.
# - srcML 1.0.0 is the Ubuntu 20.04 package the replication package installs. It is built for
#   amd64 only, so the image is linux/amd64 (on Apple silicon, Docker runs it under emulation).
# - The BFG fork with --blob-exec (dmgerman/bfg-repo-cleaner, branch blobexec, commit fbf55a1) is
#   built with its sbt 0.13.13. Its plugins moved from Bintray, which closed in 2021, to
#   repo.scala-sbt.org, which sbt-repositories points at.
# - cregit itself (the replication package's modified copy, GPL v3) is not part of the image: it is
#   mounted at /opt/cregit when the image runs.
FROM --platform=linux/amd64 eclipse-temurin:8-jdk-focal

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git wget perl \
        exuberant-ctags libxerces-c3.2 \
        libdbi-perl libdbd-sqlite3-perl libhtml-fromtext-perl libset-scalar-perl \
        libarchive13 libcurl4 libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://github.com/srcML/srcMLReleases/raw/main/srcml_1.0.0-1_ubuntu20.04.deb \
    && (dpkg -i srcml_1.0.0-1_ubuntu20.04.deb \
        || (apt-get update && apt-get -f install -y --no-install-recommends)) \
    && rm -f srcml_1.0.0-1_ubuntu20.04.deb \
    && rm -rf /var/lib/apt/lists/* \
    && srcml --version

RUN curl -fsSL https://github.com/sbt/sbt/releases/download/v1.9.9/sbt-1.9.9.tgz | tar xz -C /opt
ENV PATH=/opt/sbt/bin:$PATH
COPY sbt-repositories /root/.sbt/repositories

RUN git clone --branch blobexec https://github.com/dmgerman/bfg-repo-cleaner.git /opt/bfg-repo-cleaner \
    && cd /opt/bfg-repo-cleaner \
    && git checkout --quiet fbf55a1 \
    && sbt -Dsbt.override.build.repos=true bfg/assembly \
    && ls bfg/target/bfg-*.jar

# the repositories are bind-mounted, so their owner is not the container's user
RUN git config --system --add safe.directory '*'

COPY tokenize-repos.sh /usr/local/bin/tokenize-repos.sh
RUN chmod +x /usr/local/bin/tokenize-repos.sh
