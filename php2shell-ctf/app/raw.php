<?php
$page = $_GET['page'] ?? '';
$file = __DIR__ . '/data/' . $page;
@include($file);
