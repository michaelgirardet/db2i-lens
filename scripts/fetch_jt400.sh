#!/usr/bin/env bash
# Download the JT400 JDBC driver into ~/.db2ilens/jt400.jar (never commit the JAR).
set -euo pipefail

DEST_DIR="${HOME}/.db2ilens"
DEST_JAR="${DEST_DIR}/jt400.jar"
# Maven Central — JT400 open source (IBM Toolbox for Java)
VERSION="${JT400_VERSION:-21.0.5}"
URL="https://repo1.maven.org/maven2/net/sf/jt400/jt400/${VERSION}/jt400-${VERSION}.jar"

mkdir -p "${DEST_DIR}"
echo "Downloading JT400 ${VERSION} → ${DEST_JAR}"
curl -fsSL "${URL}" -o "${DEST_JAR}.partial"
mv "${DEST_JAR}.partial" "${DEST_JAR}"
echo "OK. export JT400_JAR=${DEST_JAR}"
