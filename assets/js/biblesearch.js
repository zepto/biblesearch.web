// Keep track of what strongs and morphology definitions are displayed so
// we don't try to display them again.
var current_strongs = '';
var current_morph = '';

/**
  * Send the search request to the server and display the verses when the
  * results come back.
  */
function search(event) {
    event.preventDefault();

    var terms = $('#form-search input[name=search]').val();
    var min_range = $('#form-range input[id=min-range]').val();
    var max_range = $('#form-range input[id=max-range]').val();

    save_state({
        'biblesearch.query': terms,
        'biblesearch.min_range': min_range,
        'biblesearch.max_range': max_range
    });

    return do_search(terms, min_range, max_range);
}

/**
    * Send the search request to the server and display the verses when the
    * results come back.
    */
function do_search(terms, min_range, max_range) {
    return $.ajax({
        url: '/biblesearch/search.json',
        type: 'GET',
        dataType: 'json',
        data: {
            search: terms,
            min_range: min_range,
            max_range: max_range,
        },
        context: $('#verses')
    })
    .done(function(response) {
        // response.references is supposed to be a list of references, if it is
        // then lookup and display all of them.
        if (response.references)
            lookup(response.references.join());
    })
    .fail(function(request, textstatus, message) {
        $(this).html(request.responseText);
    });
}

/**
  * Adjust the height of the display columns according to the windows height.
  */
function result_height() {
    var pageHeight = $(window).height();
    var navHeight = pageHeight - 60;

    $('#verses').height(navHeight);
    $('#verse_list').height(navHeight);
    $('#strongs_morph').height(navHeight);

    // $('#verses').css('max-height: ' + navHeight);
    // $('#verse_list').css('max-height: ' + navHeight);
    // $('#strongs_morph').css('max-height: ' + navHeight);

    // $('#results').scrollTop($('#results')[0].scrollHeight);
}

/**
  * Send a request to the server for the strongs and morphology definition, and
  * show the returned response in the #strongs_morph div.
  */
function show_strongs(strongs, morph) {
    return $.ajax({
        url: '/biblesearch/strongs.json',
        type: 'GET',
        dataType: 'json',
        data: {
            strongs: strongs,
            morph: morph,
        },
        context: $('#strongs_morph')
    })
    .done(function(response) {
        $(this).html(response.html);
    })
    .fail(function(request, textstatus, message) {
        $('#verses').html(request.responseText);
    });
}

/**
  * Save a value either to a cookie or localStorage.
  */
function save_state(array) {
    for (var key in array) {
        if (localStorage)
            localStorage.setItem(key, array[key]);
        else
            document.cookie = key + '=' + array[key];
    }
}

/**
  * Get a value from either a cookie or localStorage.
  */
function get_state(key) {
    if (localStorage) {
        // Try the local storage first.
        return localStorage.getItem(key);
    } else {
        // Look for the value in the cookies.
        $.each(document.cookie.split(';'), function(index, item) {
            var item_split = item.split('=');
            if (item_split[0].trim() === key)
                return item_split[1].trim();
        });
    }
    return '';
}

/**
  * Attempt to restore the previous session.
  */
function restore_session() {
    var references = get_state('biblesearch.references');
    var verse_list = get_state('biblesearch.verse_list');
    var terms = get_state('biblesearch.query');
    var min_range = get_state('biblesearch.min_range');
    var max_range = get_state('biblesearch.max_range');
    var context = get_state('biblesearch.context');

    if (min_range)
        $('#form-range input[id=min-range]').val(min_range);
    if (max_range)
        $('#form-range input[id=max-range]').val(max_range);
    if (terms)
        $('#form-search input[name=search]').val(terms);
    if (context)
        $('#form-context input[id=context]').val(context);
    if (references)
        $('#form-lookup input[name=verse_refs]').val(references);
    if (verse_list)
        lookup(verse_list);
    else if (!localStorage && terms)
        do_search(terms);

    // localStorage.clear();
}


/**
  * Send a request to the server for the text of a verse or list of verses, and
  * display the response in the #verses div.
  */
function show_verses(references) {
    // Send the search terms so the server can highlight them in the text.
    var terms = $('#form-search input[name=search]').val();
    var context = $('#form-context input[id=context]').val();

    save_state({'biblesearch.context': context});

    // Show a loading message so the user doesn't think its not loading and
    // clicks again, further slowing it.
    $('#verses').html('<div class="alert alert-info"><strong>Loading verses...</strong></div>');

    return $.ajax({
        url: '/biblesearch/lookup.json',
        type: 'GET',
        dataType: 'json',
        data: {
            verse_refs: references,
            context: context,
            terms: terms,
        },
        context: $('#verses')
    })
    .done(function(response) {
        $(this).html(response.html);

        hide_notes();

        highlight_strongs();
    })
    .fail(function(request, textstatus, message) {
        $(this).html(request.responseText);
    });
}

/**
  * Hide the notes and add icons at the end of each to toggle them on or off.
  */
function hide_notes() {
    // Hide the notes.
    $('.note').hide();
    $('.note').after('<i class="icon-plus" id="note-show"></i>');
    $('.note').prepend(' ');
}

/**
  * Send a request to the server for the daily devotional, and display the
  * response in the #verses div.
  */
function show_devotional(devotional_date) {
    return $.ajax({
        url: '/biblesearch/devotional.json',
        type: 'GET',
        dataType: 'json',
        data: {
            date: devotional_date,
        },
        context: $('#verses')
    })
    .done(function(response) {
        $(this).html(response.html);
    })
    .fail(function(request, textstatus, message) {
        $(this).html(request.responseText);
    });
}

/**
  * Highlight the word groups that match the strongs numbers in the search
  * query input.
  */
function highlight_strongs() {
    var terms = $('#form-search input[name=search]').val();
    var terms_match = terms.match(/((?:H|G)\d+)/g);

    if (terms_match)
    {
        // Highlight the queried strongs numbers in the target verses text.
        $.each(terms_match, function(num_index, strong_num) {
            // Uppercase the prefix letter of the strongs number.
            strong_num = strong_num.toUpperCase();

            // Check each word group for the strongs number and if it is
            // found put a span around it to highlight it.
            $(".target-text .word").each(function(w_index, w) {
                var lemma = $(this).attr('data-lemma');
                var matches = lemma.match(/((?:H|G)\d+)/g);

                if ($.inArray(strong_num, matches) != -1) {
                    $(this).html('<span class="strongs-highlight">' + $(this).html() + '</span>');
                }
            });
        });
    }
}

/**
  * Send a request for the context paragraph of the given verse reference, and
  * put the results on the page.
  */
function get_paragraph(verse_ref) {

    return $.ajax({
        url: '/biblesearch/paragraph.json',
        type: 'GET',
        dataType: 'json',
        data: {
            start: verse_ref,
        },
        context: $('#verse_list')
    })
    .done(function(response) {
        if (response.references)
            lookup(response.references.join());
        // Display the list of references.
        // $(this).html(response.html);
        //
        // // Open all the results.
        // show_verses($('#verse_list #verse-refs').text());
    })
    .fail(function(request, textstatus, message) {
        $(this).html(request.responseText);
    });
}

/**
  * Ask the server for the html for verse list list of references.
  */
function lookup(references) {
    save_state({'biblesearch.verse_list': references});

    // Show the verses.
    show_verses(references);

    return $.ajax({
        url: '/biblesearch/references.json',
        type: 'GET',
        dataType: 'json',
        data: {
            verse_refs: references,
        },
        context: $('#verse_list')
    })
    .done(function(response) {
        // Display the list of references.
        $(this).html(response.html);
    })
    .fail(function(request, textstatus, message) {
        $(this).html(request.responseText);
    });
}

$(function() {
    // Set the initial size.
    result_height();

    // Change the results box minimum height when the window is resized
    $(window).resize(result_height);

    hide_notes();

    // Call the search function when the search button is clicked.
    $(document).on('submit', '#form-search', search);

    // Get the context.
    $(document).on('submit', '#form-context', function(event) {
        // Build a list of all target verses and re-show them.
        var verse_refs = [];
        var context = $('#form-context input[id=context]').val();

        save_state({'biblesearch.context': context});

        $('#verses a').each(function(index, verse) {
            if ($(this).hasClass('target-verse'))
                verse_refs.push($(this).html());
        });
        if (verse_refs)
            show_verses(verse_refs.join());

        // Hide the dropdown.
        $(".dropdown.open").removeClass('open');

        event.preventDefault();
    });

    // Get the search range.
    $(document).on('submit', '#form-range', function(event) {
        // Refresh the search results.
        search(event);

        // Hide the dropdown.
        $(".dropdown.open").removeClass('open');

        event.preventDefault();
    });

    // Get a reference or list of references to lookup.
    $(document).on('submit', '#form-lookup', function(event) {
        var references = $('#form-lookup input[name=verse_refs]').val();

        save_state({'biblesearch.references': references});

        lookup(references);

        // Hide the dropdown.
        $(".dropdown.open").removeClass('open');

        event.preventDefault();
    });

    // Get the date of the devotional to display.
    $(document).on('submit', '#form-devotional', function(event) {
        var devotional_date = $('#form-devotional input[name=date]').val();

        save_state({'biblesearch.date': devotional_date});

        // Show the devotional.
        show_devotional(devotional_date);

        // Hide the dropdown.
        $(".dropdown.open").removeClass('open');

        event.preventDefault();
    });

    // Select inputs when they receive focus.
    $("input[type=text],input[type=number]").focus(function() {
        $(this).select();
    });

    // Get a list of book names from the server put them as the typeahead
    // source for the appropriate inputs.
    $.get('/biblesearch/books',
            function(response) {
                $('#min-range').typeahead({source: response.array});
                $('#max-range').typeahead({source: response.array});
                $('#form-lookup input[name=verse_refs]').typeahead({source: response.array});
            },
            'json')
    .fail(function(request, textstatus, message) {
        $('#verses').html(request.responseText);
    });

    highlight_strongs();
    restore_session();
});

/**
  * Show the strongs a morph definition of the word that was either hovered
  * over or clicked on.
  */
function show_def(strongs, morph) {
    // If they are not being display, then display them.
    if (current_strongs != strongs || current_morph != morph)
    {
        // Mark these as being displayed.
        current_strongs = strongs;
        current_morph = morph;

        // Show them.
        show_strongs(strongs, morph);
    }
}

/**
  * Add the strongs number pointed to by the target to the search query input.
  */
function append_search(lemma) {
    var search = $('#form-search input[name=search]');

    // Get all the strongs that belong to this word or group of words.
    var matches = lemma.match(/((?:H|G)\d+)/g);
    $(matches).each(function(index, value) {
        search.val(search.val() + ' +' + value);
    });

    save_state({'biblesearch.query': search.val()});
}


$(function() {
    var has_touch = $('html').hasClass('touch');

    // Display the tag definitions of the word/words under the cursor.
    $(document).on('mouseenter', '.word', function() {
        // Get the tag attributes.
        var strongs = $(this).attr("data-lemma");
        var morph = $(this).attr("data-morph");
        show_def(strongs, morph);
    });

    // Append the strongs number of the clicked word/words to the search input.
    $(document).on('click', '.word', function(event) {
        if (!$('html').hasClass('touch')) {
            // If not on a touch screen append the strongs number to the search
            // input.
            var lemma = $(this).attr("data-lemma");
            append_search(lemma);
        } else {
            // On a touch screen show the definition of the strongs and morph.
            // Get the tag attributes.
            var strongs = $(this).attr("data-lemma");
            var morph = $(this).attr("data-morph");
            show_def(strongs, morph);
        }
    });

    // Display all the verses in the list when the verse count link is clicked.
    $(document).on('click', 'a.verse-count', function(event) {
        event.preventDefault();
        var verse_list = [];
        $('#verse_list #verse-refs .verseref').each(function(index, ref) {
            verse_list.push($(this).text());
        });
        show_verses(verse_list.join());
    });

    // Display each verse when it's reference link is clicked.
    $(document).on('click', 'a.verseref', function(event) {
        event.preventDefault();
        if ($(this).hasClass('verselist')) {
            // Lookup a list of verses so they will show up on the side.
            lookup($(this).attr('href').split('=')[1]);
        } else {
            // One reference was clicked so it is probably already in the verse
            // list.
            show_verses($(this).text());
        }
    });

    // Display the definition of the strongs number link that is clicked.
    $(document).on('click', '#strongs_morph a', function(event) {
        event.preventDefault();
        if ($(this).attr('href')) {
            // This is a strongs number in the definition.
            show_strongs($(this).attr('href'), '');
        } else if ($(this).attr('data-name')) {
            // This is the strongs heading.
            var lemma = $(this).attr("data-name");
            append_search(lemma);
        }
    });

    // Display each verse when it's reference link is clicked.
    $(document).on('click', 'span.paragraph-marker', function(event) {
        var verseref = $(this).parent().prev().text();
        get_paragraph(verseref);
    });

    // Toggle the visiblity of the notes.
    $(document).on('click', '#note-show', function(event) {
        // Toggle notes visiblity.
        $(this).prev().toggle('slow');

        // Toggle the plus/minus icon.
        $(this).toggleClass(function() {
            if ($(this).hasClass('icon-plus')) {
                return 'icon-minus';
            } else {
                return 'icon-plus';
            }
        });
    });

    $(document).on('click', '#paragraph-button', function(event) {
        // Get the paragraph context for each target-verse.
        // Build a list of all target verses.
        var verse_refs = [];
        $('#verses a').each(function(index, verse) {
            if ($(this).hasClass('target-verse'))
                verse_refs.push($(this).html());
        });
        // Join the array and get the paragraph context.
        if (verse_refs)
            get_paragraph(verse_refs.join());

        // Hide the dropdown.
        $(".dropdown.open").removeClass('open');
    });

    // Focus the dropdown inputs when the dropdown is displayed.
    $(document).on('click', '#dcontext', function(event) {
        var x = setTimeout('$("#context").focus()', 100);
    });
    $(document).on('click', '#ddevotional', function(event) {
        var x = setTimeout('$("#devotional").focus()', 100);
    });
    $(document).on('click', '#dlookup', function(event) {
        var x = setTimeout('$("#lookup").focus()', 100);
    });
});
