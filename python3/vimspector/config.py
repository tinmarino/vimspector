# vimspector - A multi-language debugging system for Vim
# Copyright 2018 Ben Jackson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import string
import subprocess
import shlex

from vimspector import utils, install

VIMSPECTOR_HOME = os.path.abspath( os.path.join( os.path.dirname( __file__ ),
                                                 '..',
                                                 '..' ) )


def GetJsonFromUserCode( path_to_user_code,
                         arguments = [],
                         env = None,
                         cwd = None ):
  try:
    return json.loads( subprocess.check_output(
      [ path_to_user_code ] + arguments,
      env = env if env is not None else os.environ,
      cwd = cwd if cwd is not None else os.getcwd()
    ) )
  except Exception as e:
    utils.UserMessage( 'Exception running user code {}: {}'.format(
      path_to_user_code,
      str( e ) ) )


def GetConfigurationDatabase( directory = None ):
  launch_config_file = utils.PathToConfigFile( '.vimspector.json',
                                               directory = directory )

  if not launch_config_file:
    utils.UserMessage( 'Unable to find .vimspector.json. You need to tell '
                       'vimspector how to launch your application' )
    raise RuntimeError( 'No vimspector configuration found' )

  with open( launch_config_file, 'r' ) as f:
    database = json.load( f )

  return database, os.path.dirname( launch_config_file )


def GetAdapters( database, directory = None ):
  adapters = {}

  gadget_files = [
      install.GetGadgetConfigFile( VIMSPECTOR_HOME ),
      utils.PathToConfigFile( '.gadgets.json', directory = directory )
  ]

  for gadget_config_file in gadget_files:
    if gadget_config_file and os.path.exists( gadget_config_file ):
      with open( gadget_config_file, 'r' ) as f:
        adapters.update( json.load( f ).get( 'adapters' ) or {} )

  adapters.update( database.get( 'adapters' ) or {} )

  return adapters


def ExpandReferencesInDict( obj, mapping, **kwargs ):
  def expand_refs_in_string( s ):
    s = os.path.expanduser( s )
    s = os.path.expandvars( s )

    # Parse any variables passed in in mapping, and ask for any that weren't,
    # storing the result in mapping
    bug_catcher = 0
    while bug_catcher < 100:
      ++bug_catcher

      try:
        s = string.Template( s ).substitute( mapping, **kwargs )
        break
      except KeyError as e:
        # HACK: This is seemingly the only way to get the key. str( e ) returns
        # the key surrounded by '' for unknowable reasons.
        key = e.args[ 0 ]
        mapping[ key ] = utils.AskForInput(
          'Enter value for {}: '.format( key ) )
      except ValueError as e:
        utils.UserMessage( 'Invalid $ in string {}: {}'.format( s, e ),
                           persist = True )
        break

    return s

  def expand_refs_in_object( obj ):
    if isinstance( obj, dict ):
      ExpandReferencesInDict( obj, mapping, **kwargs )
    elif isinstance( obj, list ):
      new_list = []
      for i, _ in enumerate( obj ):
        new_obj = expand_refs_in_object( obj[ i ] )
        if isinstance( new_obj, list ):
          # insert these elements
          new_list.extend( new_obj )
        else:
          new_list.append( new_obj )
      obj = new_list
    elif isinstance( obj, str ):
      obj = expand_refs_in_string( obj )
      # HACK: Try and convert the new type to a json type. This (should?) allow
      # interpolation of things like booleans.
      try:
        new_obj = json.loads( obj )
        if not isinstance( new_obj, str ):
          obj = new_obj
      except Exception:
        pass

    return obj

  for k in obj.keys():
    obj[ k ] = expand_refs_in_object( obj[ k ] )


def ParseVariables( variables ):
  new_variables = {}
  for n, v in variables.items():
    if isinstance( v, dict ):
      if 'shell' in v:

        new_v = v.copy()
        # Bit of a hack. Allows environment variables to be used.
        ExpandReferencesInDict( new_v, {} )

        env = os.environ.copy()
        env.update( new_v.get( 'env' ) or {} )
        cmd = new_v[ 'shell' ]
        if not isinstance( cmd, list ):
          cmd = shlex.split( cmd )

        new_variables[ n ] = subprocess.check_output(
          cmd,
          cwd = new_v.get( 'cwd' ) or os.getcwd(),
          env = env ).decode( 'utf-8' ).strip()
      else:
        raise ValueError(
          "Unsupported variable defn {}: Missing 'shell'".format( n ) )
    else:
      new_variables[ n ] = v

  return new_variables
