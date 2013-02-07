$(function() {
    // Keep track of what strongs and morphology definitions are displayed so
    // we don't try to display them again.
    var current_strongs = '';
    var current_morph = '';

    // Display the tag definitions of the word/words under the cursor.
    $(document).on('mouseenter', '.word', function() {
        // Get the tag attributes.
        var strongs = $(this).attr("data-lemma");
        var morph = $(this).attr("data-morph");

        // If they are not being display, then display them.
        if (current_strongs != strongs || current_morph != morph)
        {
            // Mark these as being displayed.
            current_strongs = strongs;
            current_morph = morph;

            // Show them.
            show_strongs(strongs, morph);
        }
    });

    // Append the strongs number of the clicked word/words to the search input.
    $(document).on('click', '.word', function(event) {
        var lemma = $(this).attr("data-lemma");
        var search = $('#form-search input[name=search]');

        // Get all the strongs that belong to this word or group of words.
        var matches = lemma.match(/((?:H|G)\d+)/g);
        $(matches).each(function(index, value) {
            search.val(search.val() + ' +' + value);
        });

        if (localStorage)
            localStorage.setItem('query', search.val());
    });

    // Display all the verses in the list when the verse count link is clicked.
    $(document).on('click', 'a.verse-count', function(event) {
        event.preventDefault();
        show_verses($('#verse_list #verse-refs').text());
    });

    // Display each verse when it's reference link is clicked.
    $(document).on('click', 'a.verseref', function(event) {
        event.preventDefault();
        show_verses($(this).text());
    });

    // Display the definition of the strongs number link that is clicked.
    $(document).on('click', '#strongs_morph a', function(event) {
        event.preventDefault();
        if ($(this).attr('href'))
            show_strongs($(this).attr('href'), '');
    });

    // Display each verse when it's reference link is clicked.
    $(document).on('click', 'span.paragraph-marker', function(event) {
        var verseref = $(this).parent().prev().text();
        get_paragraph(verseref);
    });

});
