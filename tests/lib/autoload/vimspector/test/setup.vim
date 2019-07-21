function! vimspector#test#setup#SetUpWithMappings( mappings ) abort
  if exists ( 'g:loaded_vimpector' )
    unlet g:loaded_vimpector
  endif

  if a:mappings != v:none
    let g:vimspector_enable_mappings = a:mappings
  endif

  source vimrc

  " This is a bit of a hack
  runtime! plugin/**/*.vim
endfunction

function! vimspector#test#setup#ClearDown() abort
  if exists( '*vimspector#internal#state#Reset' )
    call vimspector#internal#state#Reset()
  endif
endfunction

function! vimspector#test#setup#Reset() abort
  call vimspector#Reset()
  call WaitForAssert( {->
        \ assert_true( pyxeval( '_vimspector_session._connection is None' ) )
        \ } )

  call vimspector#test#signs#AssertSignGroupEmpty( 'VimspectorCode' )
  call vimspector#ClearBreakpoints()
  call vimspector#test#signs#AssertSignGroupEmpty( 'VimspectorBP' )
endfunction

