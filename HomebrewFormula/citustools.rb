class Docker < Requirement
  fatal true
  default_formula "docker"

  satisfy { which "docker" }

  def message
    "Docker is required for this package."
  end
end

class Citustools < Formula
  desc "Tools and config used in Citus Data projects."
  homepage "https://github.com/citusdata/tools"
  url "https://github.com/citusdata/tools/archive/v0.5.0.tar.gz"
  sha256 "dd0eb39686f7c2cd61084ed3bbf52ffe7ea6fe60d715b6bf4ca3a7b775c30ec9"

  depends_on "uncrustify"
  depends_on Docker

  def install
    # FIXME: ensure installdirs runs exactly once
    ENV.deparallelize

    system "make", "install", "prefix=#{prefix}", "sysconfdir=#{etc}"
  end

  test do
    system "true"
  end
end
