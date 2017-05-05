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
  url "https://github.com/citusdata/tools/archive/v0.6.0.tar.gz"
  sha256 "85644f4910e17ed378748d930cf86e98b9316243467c8a6f009de8001a5bdbff"

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
