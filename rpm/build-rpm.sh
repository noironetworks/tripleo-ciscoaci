#!/bin/bash
# Should be run from the root of the source tree

if [ ! -d rpm ]; then
   echo "Directory 'rpm' not found"
   exit 1
fi
SPEC_FILE=`ls rpm/*.spec`
if [ -z $SPEC_FILE ]; then
   echo "RPM spec file not found"
   exit 1
fi
RELEASE=${RELEASE:-1}
BUILD_DIR=${BUILD_DIR:-`pwd`/rpmbuild}
mkdir -p $BUILD_DIR/BUILD $BUILD_DIR/SOURCES $BUILD_DIR/SPECS $BUILD_DIR/RPMS $BUILD_DIR/SRPMS
cp $SPEC_FILE $BUILD_DIR/SPECS/
SPEC_FILE=${SPEC_FILE/rpm\//}
NAME=tripleo-ciscoaci
tar czf $BUILD_DIR/SOURCES/$NAME.tar.gz $NAME
rpmbuild --clean -ba --define "_topdir $BUILD_DIR" --define "release $RELEASE" $BUILD_DIR/SPECS/$SPEC_FILE
